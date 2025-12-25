"""
WebSocket consumers for real-time updates.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


class DownloadProgressConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for download progress updates.
    Replicates the real-time progress functionality from the original app.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.download_id = self.scope['url_route']['kwargs']['download_id']
        self.group_name = f"download_progress_{self.download_id}"
        self.user = self.scope['user']

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Check if user has access to this download
        has_access = await self.check_download_access()
        if not has_access:
            await self.close(code=4003)
            return

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected for download {self.download_id} by user {self.user.id}")

        # Send current download status
        await self.send_current_status()

    async def check_download_access(self) -> bool:
        """
        Check if user has access to the download.

        Returns:
            True if user has access
        """
        try:
            from apps.downloads.models import DownloadTask
            download_task = await database_sync_to_async(
                DownloadTask.objects.filter(
                    id=self.download_id,
                    user=self.user
                ).exists
            )()
            return download_task
        except Exception as e:
            logger.error(f"Error checking download access: {e}")
            return False

    async def send_current_status(self) -> None:
        """
        Send current download status to the client.
        """
        try:
            from apps.downloads.models import DownloadTask
            download_task = await database_sync_to_async(
                DownloadTask.objects.get
            )(id=self.download_id)

            await self.send(text_data=json.dumps({
                'type': 'download_status',
                'download_id': str(download_task.id),
                'status': download_task.status,
                'progress_percentage': download_task.progress_percentage,
                'downloaded_items': download_task.downloaded_items,
                'total_items': download_task.total_items,
                'download_speed': download_task.download_speed,
                'error_message': download_task.error_message
            }))
        except Exception as e:
            logger.error(f"Error sending current status: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to get download status'
            }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"WebSocket disconnected for download {self.download_id}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))

            elif message_type == 'request_status':
                await self.send_current_status()

            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    async def download_progress(self, event):
        """Handle download progress updates from group."""
        await self.send(text_data=json.dumps({
            'type': 'progress_update',
            'download_id': event['download_id'],
            'status': event['status'],
            'percentage': event['percentage'],
            'message': event['message'],
            'timestamp': event['timestamp'],
            'details': event.get('details', {})
        }))

    async def download_status(self, event):
        """Handle download status changes."""
        await self.send(text_data=json.dumps({
            'type': 'status_change',
            'download_id': event['download_id'],
            'status': event['status'],
            'message': event.get('message', ''),
            'timestamp': event['timestamp']
        }))

    async def download_error(self, event):
        """Handle download errors."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'download_id': event['download_id'],
            'error_message': event['error_message'],
            'timestamp': event['timestamp']
        }))

    async def download_speed(self, event):
        """Handle download speed updates."""
        await self.send(text_data=json.dumps({
            'type': 'speed_update',
            'download_id': event['download_id'],
            'speed': event['speed'],
            'speed_formatted': event['speed_formatted'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def check_download_access(self):
        """Check if user has access to this download."""
        try:
            from apps.downloads.models import DownloadTask
            download_task = DownloadTask.objects.get(id=self.download_id, user=self.user)
            return True
        except DownloadTask.DoesNotExist:
            return False

    @database_sync_to_async
    def get_download_status(self):
        """Get current download status."""
        try:
            from apps.downloads.models import DownloadTask
            from apps.downloads.serializers import DownloadTaskSerializer

            download_task = DownloadTask.objects.get(id=self.download_id, user=self.user)
            serializer = DownloadTaskSerializer(download_task)
            return serializer.data
        except DownloadTask.DoesNotExist:
            return None

    async def send_current_status(self):
        """Send current download status to client."""
        status_data = await self.get_download_status()
        if status_data:
            await self.send(text_data=json.dumps({
                'type': 'current_status',
                'download_task': status_data
            }))


class UserNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user notifications.
    Handles global notifications for the user.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.user = self.scope['user']

        # Check if user is authenticated and accessing own notifications
        if not self.user.is_authenticated or self.user.id != self.user_id:
            await self.close(code=4001)
            return

        self.group_name = f"user_notifications_{self.user_id}"

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"Notification WebSocket connected for user {self.user_id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"Notification WebSocket disconnected for user {self.user_id}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))

            elif message_type == 'mark_notification_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error handling notification message: {e}")

    async def download_notification(self, event):
        """Handle download completion notifications."""
        await self.send(text_data=json.dumps({
            'type': 'download_completed',
            'title': event['title'],
            'message': event['message'],
            'download_path': event['download_path'],
            'course_image': event['course_image'],
            'timestamp': event['timestamp']
        }))

    async def system_notification(self, event):
        """Handle system notifications."""
        await self.send(text_data=json.dumps({
            'type': 'system_notification',
            'level': event['level'],  # info, warning, error
            'title': event['title'],
            'message': event['message'],
            'timestamp': event['timestamp']
        }))

    async def update_notification(self, event):
        """Handle update notifications."""
        await self.send(text_data=json.dumps({
            'type': 'update_available',
            'version': event['version'],
            'download_url': event['download_url'],
            'release_notes': event['release_notes'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read."""
        # TODO: Implement notification read tracking if needed
        pass


class DownloadControlConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for download control commands.
    Handles pause/resume/cancel commands.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.download_id = self.scope['url_route']['kwargs']['download_id']
        self.user = self.scope['user']

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Check if user has access to this download
        has_access = await self.check_download_access()
        if not has_access:
            await self.close(code=4003)
            return

        self.group_name = f"download_control_{self.download_id}"

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"Control WebSocket connected for download {self.download_id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"Control WebSocket disconnected for download {self.download_id}")

    async def receive(self, text_data):
        """Handle incoming control commands."""
        try:
            data = json.loads(text_data)
            command = data.get('command')

            if command == 'pause':
                await self.handle_pause_command()
            elif command == 'resume':
                await self.handle_resume_command()
            elif command == 'cancel':
                await self.handle_cancel_command()
            else:
                logger.warning(f"Unknown control command: {command}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error handling control command: {e}")

    async def download_control(self, event):
        """Handle control commands from the download task."""
        await self.send(text_data=json.dumps({
            'type': 'control_acknowledged',
            'action': event['action'],
            'download_id': event['download_id'],
            'timestamp': event['timestamp']
        }))

    async def handle_pause_command(self):
        """Handle pause command."""
        # Update database
        success = await self.update_download_status('paused')
        if success:
            # Broadcast to all consumers for this download
            await self.channel_layer.group_send(
                f"download_progress_{self.download_id}",
                {
                    'type': 'download_status',
                    'download_id': str(self.download_id),
                    'status': 'paused',
                    'message': 'Download paused by user',
                    'timestamp': self.get_timestamp()
                }
            )

    async def handle_resume_command(self):
        """Handle resume command."""
        # Update database
        success = await self.update_download_status('downloading')
        if success:
            # Broadcast to all consumers for this download
            await self.channel_layer.group_send(
                f"download_progress_{self.download_id}",
                {
                    'type': 'download_status',
                    'download_id': str(self.download_id),
                    'status': 'downloading',
                    'message': 'Download resumed by user',
                    'timestamp': self.get_timestamp()
                }
            )

    async def handle_cancel_command(self):
        """Handle cancel command."""
        # Update database and cancel Celery task
        success = await self.cancel_download_task()
        if success:
            # Broadcast to all consumers for this download
            await self.channel_layer.group_send(
                f"download_progress_{self.download_id}",
                {
                    'type': 'download_status',
                    'download_id': str(self.download_id),
                    'status': 'cancelled',
                    'message': 'Download cancelled by user',
                    'timestamp': self.get_timestamp()
                }
            )

    @database_sync_to_async
    def check_download_access(self):
        """Check if user has access to this download."""
        try:
            from apps.downloads.models import DownloadTask
            download_task = DownloadTask.objects.get(id=self.download_id, user=self.user)
            return True
        except DownloadTask.DoesNotExist:
            return False

    @database_sync_to_async
    def update_download_status(self, status):
        """Update download status in database."""
        try:
            from apps.downloads.models import DownloadTask
            download_task = DownloadTask.objects.get(id=self.download_id, user=self.user)
            download_task.status = status
            download_task.save()
            return True
        except DownloadTask.DoesNotExist:
            return False

    @database_sync_to_async
    def cancel_download_task(self):
        """Cancel download task and Celery task."""
        try:
            from apps.downloads.models import DownloadTask
            download_task = DownloadTask.objects.get(id=self.download_id, user=self.user)

            # Cancel Celery task if running
            if download_task.celery_task_id:
                from celery import current_app
                current_app.control.revoke(download_task.celery_task_id, terminate=True)

            download_task.status = 'cancelled'
            download_task.save()
            return True

        except DownloadTask.DoesNotExist:
            return False

    def get_timestamp(self):
        """Get current timestamp."""
        from django.utils import timezone
        return timezone.now().isoformat()


class LoggerConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time log streaming.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope['user']

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = "logger_stream"

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"Logger WebSocket connected for user {self.user.id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"Logger WebSocket disconnected for user {self.user.id}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error handling logger message: {e}")

    async def log_entry(self, event):
        """Handle new log entry."""
        await self.send(text_data=json.dumps({
            'type': 'log_entry',
            'log_entry': event['log_entry'],
            'timestamp': event['timestamp']
        }))


class GlobalStatsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for global application statistics.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope['user']

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = f"global_stats_{self.user.id}"

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"Stats WebSocket connected for user {self.user.id}")

        # Send initial stats
        await self.send_current_stats()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"Stats WebSocket disconnected for user {self.user.id}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))

            elif message_type == 'request_stats':
                await self.send_current_stats()

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error handling stats message: {e}")

    async def stats_update(self, event):
        """Handle stats updates."""
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': event['stats'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def get_user_stats(self):
        """Get current user statistics."""
        try:
            from apps.downloads.models import DownloadTask
            from apps.courses.models import UserCourse

            user_downloads = DownloadTask.objects.filter(user=self.user)
            user_courses = UserCourse.objects.filter(user=self.user)

            stats = {
                'total_courses': user_courses.count(),
                'downloaded_courses': user_courses.filter(is_downloaded=True).count(),
                'total_downloads': user_downloads.count(),
                'active_downloads': user_downloads.filter(
                    status__in=['pending', 'preparing', 'downloading', 'paused']
                ).count(),
                'completed_downloads': user_downloads.filter(status='completed').count(),
                'failed_downloads': user_downloads.filter(status='failed').count(),
                'total_size': sum(task.total_size for task in user_downloads),
                'downloaded_size': sum(task.downloaded_size for task in user_downloads),
            }

            # Calculate current download speed
            active_downloads = user_downloads.filter(status='downloading')
            if active_downloads.exists():
                total_speed = sum(task.download_speed for task in active_downloads)
                stats['current_speed'] = total_speed
            else:
                stats['current_speed'] = 0

            return stats

        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

    async def send_current_stats(self):
        """Send current statistics to client."""
        stats = await self.get_user_stats()
        if stats:
            await self.send(text_data=json.dumps({
                'type': 'current_stats',
                'stats': stats,
                'timestamp': self.get_timestamp()
            }))

    def get_timestamp(self):
        """Get current timestamp."""
        from django.utils import timezone
        return timezone.now().isoformat()


class LoggerConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time log streaming.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope['user']

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = "logger_stream"

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"Logger WebSocket connected for user {self.user.id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"Logger WebSocket disconnected for user {self.user.id}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error handling logger message: {e}")

    async def log_entry(self, event):
        """Handle new log entry."""
        await self.send(text_data=json.dumps({
            'type': 'log_entry',
            'log_entry': event['log_entry'],
            'timestamp': event['timestamp']
        }))