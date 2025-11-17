# Chat Service API

A production-ready, scalable chat service built with Django 5, Django REST Framework, Django Channels, and PostgreSQL. Features real-time messaging, file attachments, user presence, and comprehensive notification system.

> [!IMPORTANT]
> Client is available at [USClient](https://github.com/MohammadrezaAmani/usclient)

## 🚀 Features

- **Real-time Chat**: WebSocket-based messaging with Django Channels
- **User Authentication**: JWT-based authentication with SimpleJWT
- **Room Management**: Support for private (1-on-1) and group chats
- **File Attachments**: Upload images, videos, audio, documents
- **User Presence**: Online/offline status and typing indicators
- **Notifications**: Real-time push notifications
- **Message History**: Pagination and search functionality
- **Scalable Architecture**: Redis for caching and WebSocket channel layer
- **Background Tasks**: Celery for async processing
- **Docker Support**: Complete containerized deployment
- **Production Ready**: Comprehensive logging, security, and monitoring

## 📋 Requirements

- Python 3.14+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (for containerized deployment)

## 🛠 Installation

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd chat-service
   ```

2. **Create environment file:**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services:**

   ```bash
   docker-compose up -d
   ```

4. **Run migrations:**

   ```bash
   docker-compose exec django uv run python manage.py migrate
   ```

5. **Create superuser:**

   ```bash
   docker-compose exec django uv run python manage.py createsuperuser
   ```

### Option 2: Local Development

1. **Clone and setup:**

   ```bash
   git clone <repository-url>
   cd chat-service
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install uv
   uv sync
   ```

2. **Setup environment:**

   ```bash
   cp .env.example .env
   # Configure your .env file
   ```

3. **Setup database:**

   ```bash
   # Make sure PostgreSQL and Redis are running
   uv run python manage.py migrate
   uv run python manage.py createsuperuser
   ```

4. **Run development server:**

   ```bash
   uv run python manage.py runserver
   ```

5. **Run Celery worker (in another terminal):**

   ```bash
   uv run celery -A config worker --loglevel=info
   ```

6. **Run Celery beat (in another terminal):**

   ```bash
   uv run celery -A config beat --loglevel=info
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `DB_NAME` | PostgreSQL database name | `chat_db` |
| `DB_USER` | PostgreSQL username | `amani` |
| `DB_PASSWORD` | PostgreSQL password | `chat_password` |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/0` |
| `CORS_ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:3000` |
| `USE_S3` | Use S3 for file storage | `False` |
| `AWS_ACCESS_KEY_ID` | AWS access key | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | - |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket name | - |

## 📚 API Documentation

### Authentication Endpoints

#### Register User

```http
POST /api/auth/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "password_confirm": "password123",
  "first_name": "John",
  "last_name": "Doe"
}
```

#### Login

```http
POST /api/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

#### Refresh Token

```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "refresh_token_here"
}
```

### Chat Room Endpoints

#### List/Create Rooms

```http
GET /api/chat/rooms/  # List user's rooms
POST /api/chat/rooms/  # Create new room
```

#### Room Details

```http
GET /api/chat/rooms/{id}/  # Room details
PUT /api/chat/rooms/{id}/  # Update room
DELETE /api/chat/rooms/{id}/  # Delete room
```

#### Room Messages

```http
GET /api/chat/rooms/{id}/messages/?search=query&page=1  # Get messages
```

#### Join/Leave Room

```http
POST /api/chat/rooms/{id}/join/
POST /api/chat/rooms/{id}/leave/
```

### Message Endpoints

#### Send Message

```http
POST /api/chat/messages/
Content-Type: application/json

{
  "room_id": 1,
  "content": "Hello, world!",
  "reply_to": null
}
```

#### Edit/Delete Message

```http
PATCH /api/chat/messages/{id}/edit/
DELETE /api/chat/messages/{id}/soft_delete/
```

### Attachment Endpoints

#### Upload Attachment

```http
POST /api/chat/upload-attachment/
Content-Type: multipart/form-data

room_id: 1
file: <file_data>
```

### Notification Endpoints

#### List Notifications

```http
GET /api/notifications/
```

#### Mark as Read

```http
POST /api/notifications/{id}/mark_read/
POST /api/notifications/mark_all_read/
```

#### Unread Count

```http
GET /api/notifications/unread_count/
```

## 🌐 WebSocket API

### Connection

Connect to WebSocket with JWT token:

```text
ws://localhost:8000/chat/{room_id}/?token={jwt_access_token}
```

### Message Types

#### Join Room

```json
{
  "type": "join"
}
```

#### Leave Room

```json
{
  "type": "leave"
}
```

#### Send Message

```json
{
  "type": "message",
  "data": {
    "content": "Hello, world!",
    "reply_to": null
  }
}
```

#### Send Attachment

```json
{
  "type": "attachment",
  "data": {
    "message_id": null,
    "filename": "image.jpg",
    "file_url": "/media/attachments/image.jpg",
    "file_type": "image",
    "file_size": 1024000
  }
}
```

#### Typing Indicator

```json
{
  "type": "typing",
  "data": {
    "is_typing": true
  }
}
```

### Notification WebSocket

Connect to notifications:

```text
ws://localhost:8000/notifications/?token={jwt_access_token}
```

## 🔧 Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=apps --cov-report=html

# Run specific app tests
uv run pytest apps/accounts/tests.py
```

### Code Quality

```bash
# Format code
uv run black .

# Sort imports
uv run isort .

# Type checking
uv run mypy .
```

### Database Migrations

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure `SECRET_KEY`
- [ ] Setup PostgreSQL and Redis
- [ ] Configure AWS S3 (optional)
- [ ] Setup domain and SSL
- [ ] Configure email settings
- [ ] Setup monitoring and logging
- [ ] Configure backup strategy

### Docker Production Deployment

1. **Update environment variables in `.env`:**

   ```bash
   DEBUG=False
   SECRET_KEY=your-production-secret-key
   ALLOWED_HOSTS=yourdomain.com
   USE_S3=True
   # Configure AWS settings
   ```

2. **Deploy:**

   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

3. **Setup SSL with Nginx:**

   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       return 301 https://$server_name$request_uri;
   }

   server {
       listen 443 ssl;
       server_name yourdomain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /ws/ {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health/
```

### Logs

```bash
# Django logs
tail -f logs/django.log

# Docker logs
docker-compose logs -f django
docker-compose logs -f celery_worker
```

## 🔒 Security

- JWT authentication with token blacklisting
- CORS protection
- SQL injection prevention
- XSS protection
- CSRF protection
- File upload validation
- Rate limiting (implement as needed)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:

- Create an issue on GitHub
- Check the documentation
- Review the code comments

## 📈 Roadmap

- [ ] Message reactions
- [ ] Message threads
- [ ] Voice messages
- [ ] Video calls
- [ ] Admin dashboard
- [ ] Push notifications (mobile)
- [ ] Message encryption
- [ ] File sharing improvements
