# Stocker

A portfolio and stock tracking application built with Django REST API and Vue.js.

## Features

- Portfolio tracking with multi-currency support (USD, HKD)
- Transaction management (buy/sell/dividends)
- Real-time price updates via yfinance
- FIFO profit/loss calculation
- CSV import functionality
- More are coming

## Tech Stack

- **Backend**: Django, Django REST Framework, PostgreSQL
- **Frontend**: Vue 3, Vite, Tailwind CSS
- **DevOps**: Docker, Docker Compose

## Prerequisites

- Docker and Docker Compose (recommended)
- Or: Python 3.8+, Node.js 18+, PostgreSQL 15+

## Installation

### Using Docker (Recommended)

1. Clone the repository
   ```bash
   git clone <repository-url>
   cd tom_stocker
   ```

2. Create environment file
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and configure:
   ```env
   POSTGRES_DB=stocker
   POSTGRES_USER=stocker_user
   POSTGRES_PASSWORD=your_password_here
   DATABASE_URL=postgres://stocker_user:your_password_here@db:5432/stocker
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```

3. Build and start containers
   ```bash
   docker-compose up --build
   ```

4. Run database migrations
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

5. Create superuser (optional)
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

### Manual Setup

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Access

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Django Admin: http://localhost:8000/admin

## Development

### Import Transactions from CSV

```bash
docker-compose exec backend python manage.py import_trades /path/to/trades.csv
```

### Run Tests

```bash
docker-compose exec backend python manage.py test
```

### Build for Production

```bash
cd frontend
npm run build
```

## Author

**Tom Sin**

- GitHub: [@tomsin9](https://github.com/tomsin9)
- Email: contact@tomsinp.com

## License

See [LICENSE](LICENSE) file for details.
