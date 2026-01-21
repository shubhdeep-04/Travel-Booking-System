# 🏨 Travel Booking & Ticket Reservation System  

*A full-stack Django-based platform for booking hotels, cars, buses, and trains — built with scalability, clean architecture, and real-world practices.*

---

## 🚀 Live Demo  
**🔗 Live URL:** [Coming Soon] | **🎬 Demo Video:** [Watch Walkthrough](#)  

---

## 📌 Overview  
This is a **complete travel booking ecosystem** that allows users to search, compare, and book multiple travel services in one place. Think of it as a mini **MakeMyTrip/Goibibo** built with Django, PostgreSQL, and modern web practices.  

✅ **Hotel Booking** – Search, filter, room selection, availability check  
✅ **Car Rentals** – Browse cars, select dates, insurance options  
✅ **Bus Tickets** – Route search, seat selection, boarding points  
✅ **Train Tickets** – PNR generation, coach selection, RAC/Waitlist  
✅ **Unified Dashboard** – All bookings in one place  
✅ **Admin Panel** – Manage inventory, bookings, analytics  
✅ **Payment Simulation** – Secure payment flow (demo mode)  

---

## 🏗️ System Architecture  

```bash
travel_booking_system/
├── apps/
│   ├── users/           # Authentication & profiles
│   ├── hotels/          # Hotel CRUD, room management
│   ├── cars/            # Car rental, pricing, availability
│   ├── buses/           # Bus routes, seat management
│   ├── trains/          # Train schedules, PNR generation
│   ├── bookings/        # Unified booking logic
│   ├── payments/        # Payment processing
│   └── dashboard/       # Analytics & reports
├── templates/           # HTML templates (Bootstrap 5)
├── static/              # CSS, JS, images
└── media/               # Uploaded files
```

---

## 🛠️ Tech Stack  

| Category       | Technology |
|----------------|------------|
| **Backend**    | Django 4.2, Django REST Framework |
| **Database**   | PostgreSQL (production), SQLite (development) |
| **Frontend**   | HTML5, CSS3, JavaScript, Bootstrap 5 |
| **Authentication** | Django Auth, Custom User Model |
| **Payments**   | Simulated payment gateway (Stripe/PayPal ready) |
| **Deployment** | Docker, Gunicorn, Nginx, Whitenoise |
| **Tools**      | Git, GitHub, VS Code, PostgreSQL |

---

## ✨ Key Features  

### 🔐 User Features  
- **Registration/Login** – Email verification, profile management  
- **Multi-service Search** – Unified search across hotels/cars/buses/trains  
- **Smart Booking** – Real-time availability checks  
- **Booking Management** – View, modify, cancel bookings  
- **Invoice Generation** – Download booking tickets/PDF invoices  
- **Reviews & Ratings** – Rate services, view others’ feedback  

### ⚙️ Admin Features  
- **Inventory Management** – Add/update hotels, cars, buses, trains  
- **Booking Oversight** – View all bookings, update statuses  
- **Revenue Analytics** – Dashboard with charts and reports  
- **Cancellation Management** – Process refunds, update inventory  
- **User Management** – View users, assign roles  

### 🧠 Advanced Features  
- **Transaction-safe Booking** – Prevents overbooking with atomic transactions  
- **Dynamic Pricing** – Seasonal rates, discounts, promo codes  
- **Seat/Room Locking** – Temporary holds during payment  
- **PNR Generation** – Unique booking references  
- **Email Notifications** – Booking confirmations, reminders  
- **RESTful APIs** – Ready for mobile app integration  

---

## 📊 Database Schema (Core Tables)  

```sql
User (id, email, role, phone, ...)
Hotel (id, name, location, rating, ...)
HotelRoom (id, hotel_id, type, price, availability)
Car (id, model, brand, price_per_day, ...)
Bus (id, route_from, route_to, seats, ...)
Train (id, train_number, route, seats, ...)
Booking (id, user_id, service_type, service_id, dates, amount, status)
Payment (id, booking_id, amount, status, ...)
```

---

## 🚦 Getting Started  

### Prerequisites  
- Python 3.10+  
- PostgreSQL or SQLite  
- Git  

### Installation  

```bash
# 1. Clone repository
git clone https://github.com/yourusername/travel-booking-system.git
cd travel-booking-system

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 5. Run migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Run development server
python manage.py runserver
```

Visit `http://localhost:8000` to see the application.

---

## 📁 Project Structure  

```
travel_booking_system/
├── manage.py
├── requirements.txt
├── .venv
├── travel_booking_system/
│   ├── settings.py          # Project settings
│   ├── urls.py              # Main URL routing
│   └── wsgi.py
├── apps/                    # Django applications
│   ├── users/               # User authentication
│   ├── hotels/              # Hotel management
│   ├── cars/                # Car rentals
│   ├── buses/               # Bus bookings
│   ├── trains/              # Train bookings
│   ├── bookings/            # Unified booking system
│   ├── payments/            # Payment processing
│   └── dashboard/           # Analytics dashboard
├── templates/               # HTML templates
├── static/                  # Static assets
├── media/                   # Uploaded files
└── README.md
```

---

## 🧪 Testing  

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.users
python manage.py test apps.hotels

# Run with coverage
coverage run manage.py test
coverage report
```

---

## 🚀 Deployment  

### Option 1: Traditional Deployment  
```bash
# Collect static files
python manage.py collectstatic

# Run with Gunicorn
gunicorn travel_booking_system.wsgi:application

# Configure Nginx
# See deployment/nginx.conf.example
```

### Option 2: Docker Deployment  
```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d
```

---

## 📈 Future Enhancements  
- [ ] **Mobile App** – React Native/Ionic frontend  
- [ ] **AI Recommendations** – ML-based travel suggestions  
- [ ] **Live Tracking** – Real-time bus/train tracking  
- [ ] **Loyalty Program** – Points, rewards, discounts  
- [ ] **Multi-language** – Internationalization support  
- [ ] **API Gateway** – Microservices architecture  

---

## 🎯 Why This Project Stands Out  

### ✅ **Industry-Ready Architecture**  
- Modular design with separate apps for each service  
- Shared booking logic across services  
- Scalable database design with proper indexes  

### ✅ **Production-Grade Features**  
- Transaction-safe booking to prevent overbooking  
- Comprehensive admin dashboard with analytics  
- Email notifications and invoice generation  

### ✅ **Portfolio Showcase**  
- **Full-stack development** – Backend, frontend, database  
- **Real-world problem solving** – Inventory management, pricing logic  
- **Clean code** – Follows Django best practices and PEP 8  

### ✅ **Interview Ready**  
- Common interview topics covered:  
  - Database design and optimization  
  - Transaction management  
  - REST API design  
  - Authentication & authorization  
  - Payment integration  

---

## 📄 License  
This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments  
- Django documentation and community  
- Bootstrap for frontend components  
- Font Awesome for icons  
- All open-source libraries used in this project  

---

## 📞 Contact & Support  

**Project Maintainer:** Shubhdeep Singh 
**Email:** shubhdeep422@gmail.com  
**LinkedIn:** [Shubhdeep Singh](https://www.linkedin.com/in/shubhdeep-singh-3708b63a3/)  
**GitHub:** [@shubhdeep-04](https://github.com/shubhdeep-04)  

Found a bug? Please open an issue on GitHub.  
Want to contribute? Fork the repo and submit a PR!  

---

## ⭐ Show Your Support  
If you find this project useful, please give it a star on GitHub!  

[![GitHub Stars](https://img.shields.io/github/stars/shubhdeep-04/travel-booking-system?style=social)](https://github.com/yourusername/travel-booking-system)  

---

**Built with ❤️ using Django** • **Perfect for final-year projects & job interviews**