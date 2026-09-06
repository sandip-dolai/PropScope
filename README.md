<div align="center">
  <h1>🌍 PropScope</h1>
  <p><b>An Advanced Spatial Intelligence & Real Estate Market Analytics Platform</b></p>
  <p><i>A comprehensive Geographic Information System (GIS) solution bridging the gap between property search, deterministic location scoring, and high-density market analytics.</i></p>
</div>

---

## 📑 Abstract (Project Overview)

**PropScope** is an enterprise-grade, spatial intelligence real estate platform engineered to transform how buyers, agents, and administrators interact with real property data. Moving beyond traditional list-based property portals, PropScope implements a **map-first, GIS-driven** architecture powered by **PostGIS** and **Django**. 

The core purpose of this project is to solve the "Location Context Problem" in real estate. It achieves this by aggregating thousands of geospatial data points—such as proximity to transport hubs, healthcare facilities, education centers, and commercial zones—to generate **Deterministic Location Scores** and real-time **Viewport Market Analytics**. 

Designed as a Modular Monolith, the system supports complex multi-persona workflows (Buyers, Licensed Agents, Platform Admins) while maintaining strict object-level security, spatial query optimization, and a highly interactive, responsive frontend.

---

## 🎯 Core Objectives & Purpose

1. **Contextualize Real Estate via GIS:** Provide buyers with immediate visual and statistical context regarding a property's surroundings using advanced K-Nearest Neighbor (KNN) spatial queries.
2. **Standardize Location Quality:** Introduce an objective, multi-pillar Location Scoring algorithm (Transport, Healthcare, Education, Shopping, Recreation) to quantify the qualitative value of a neighborhood.
3. **Empower Agents & Admins:** Deliver a comprehensive CRM and Command Center to manage high-density property inventory, inbound leads, portfolio analytics, and platform governance.
4. **Real-Time Market Transparency:** Give users institutional-grade tools like dynamic spatial bounding-box (BBOX) market analytics and property density heatmaps.

---

## 🚀 Key Features & Capabilities

### 1. Spatial Intelligence & GIS Core
- **PostGIS KNN Engine:** Calculates the exact geodetic distance to the nearest critical amenities (Metro, Hospitals, Schools, Parks, Malls) for every property in milliseconds.
- **Viewport Dynamic Loading:** The Leaflet map drives the data. As the user pans and zooms, bounding box (BBOX) spatial queries fetch and render active assets dynamically.
- **Neighborhood MultiPolygons:** Strict geographical area mapping ensuring properties belong to accurate, localized submarkets.

### 2. Deterministic Location Scoring & Recommendations
- **Multi-Pillar Algorithm:** Evaluates a property across 5 configurable lifestyle pillars, resulting in a composite 0-100 score.
- **Weight Adjustments:** Users can dynamically adjust the weight of specific pillars (e.g., prioritizing Healthcare over Recreation) to generate personalized property recommendations.
- **Proximity Matrix:** Visual slide-over drawers detailing exact distances and travel estimates to nearby infrastructure.

### 3. Real-Time Market Analytics & Heatmaps
- **Spatial Data Aggregation:** Instantly computes Median Price, Average Price, Price-per-Sqft, and Asset Distribution for any geographical bounding box viewed on the map.
- **Density Heatmaps:** Visualizes property price density and concentration dynamically overlaying the interactive Leaflet map.
- **Property Comparison Engine:** Side-by-side parametric comparison of up to 4 properties, highlighting metric differentials and location scores.

### 4. Role-Based Personas & Workflows
- **For Buyers:** Geofenced Saved Searches, 1-Click Favorites, and automated lead/inquiry generation directed to listing agents.
- **For Agents:** A private Dashboard Command Center featuring pipeline metrics, lead CRM, image gallery management, and asset inventory controls.
- **For Admins:** Platform governance console for user moderation, agent verification, amenity curation, and global portfolio analytics.

---

## 🏗 Technical Architecture

PropScope is built on a highly optimized **Modular Monolith** pattern to ensure rapid development, tight data integrity, and high performance spatial querying.

- **Backend Framework:** Django 5.x (Python 3.12)
- **Database / GIS:** PostgreSQL 15 + PostGIS 3 (Containerized)
- **API Layer:** Django Rest Framework (DRF) with drf-spectacular (OpenAPI / Swagger)
- **Frontend Core:** Vanilla JS, HTML5, Leaflet.js (Web Mapping)
- **Styling:** Tailwind CSS (Utility-First, Native Dark/Light Mode)
- **Infrastructure:** Docker & Docker Compose orchestration

---

## ⚙️ Installation & Local Setup

To run PropScope locally for development or demonstration purposes, ensure you have **Docker** and **Docker Compose** installed.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/PropScope.git
cd PropScope
```

### 2. Build and Launch Containers
The project uses a standard `docker-compose.yml` to spin up the Django web server and the PostGIS database.
```bash
docker-compose up --build -d
```

### 3. Run Database Migrations
Apply the relational and spatial database schemas.
```bash
docker-compose exec web python manage.py migrate
```

### 4. Seed the Database (Optional but Recommended)
Populate the database with mock users, agents, amenities, and spatial properties.
```bash
docker-compose exec web python manage.py seed_db
```

### 5. Access the Platform
- **Main Application:** `http://localhost:8000/`
- **Admin Panel:** `http://localhost:8000/admin/`
- **API Documentation (Swagger):** `http://localhost:8000/api/docs/swagger/`

---

## 🗺️ Project Development Roadmap

**PropScope is currently at the completion of Phase 7.**

- ✅ **Phase 1:** Foundation (Docker, Django Scaffold, PostGIS, User Roles)
- ✅ **Phase 2:** GIS Core (Spatial Queries, Leaflet Interactivity)
- ✅ **Phase 3:** Amenities & Intelligence (KNN Engine, Neighborhoods)
- ✅ **Phase 4:** Authentication & Buyer Persona (Drawers, Favorites, Saved Searches)
- ✅ **Phase 5:** Agent & Admin Command Center (CRM, Dashboards, Moderation)
- ✅ **Phase 6:** Location Scoring & Recommendations (Deterministic Algorithms)
- ✅ **Phase 7:** Comparison & Spatial Analytics (Heatmaps, BBOX Aggregations, Matrix)
- ⏳ **Phase 8:** AI & Hybrid Recommendation Layer (Upcoming)
- ⏳ **Phase 9:** Production Engineering & System Hardening (Upcoming)

---
*PropScope — Mapping the future of real estate intelligence.*
