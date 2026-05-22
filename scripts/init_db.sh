#!/usr/bin/env bash
# ============================================================
# GestureMed AI — Database Initialisation Script
# Run this once after first docker-compose up to create
# all tables and (optionally) seed a test admin account.
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🏥 GestureMed AI — Database Init"
echo "================================="

# Wait for postgres to be ready
echo "⏳ Waiting for PostgreSQL..."
until docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T postgres \
  pg_isready -U "${POSTGRES_USER:-gesturemed}" -d "${POSTGRES_DB:-gesturemed}" > /dev/null 2>&1; do
  sleep 2
done
echo "✅ PostgreSQL ready"

# Run Alembic migrations
echo "🔄 Running database migrations..."
docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T backend \
  alembic upgrade head
echo "✅ Migrations complete"

# Seed test data (only in development)
if [ "${ENVIRONMENT:-development}" = "development" ]; then
  echo ""
  echo "🌱 Seeding development data..."
  docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T backend python - << 'PYEOF'
import asyncio
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import User, UserRole, DoctorProfile, PatientProfile
from sqlalchemy import select

async def seed():
    async with AsyncSessionLocal() as db:
        # Check if admin already exists
        result = await db.execute(select(User).where(User.email == "admin@gesturemed.ai"))
        if result.scalar_one_or_none():
            print("  Seed data already exists — skipping.")
            return

        # Admin user
        admin = User(
            email="admin@gesturemed.ai",
            hashed_password=hash_password("Admin123!"),
            full_name="System Admin",
            role=UserRole.ADMIN,
            is_verified=True,
        )
        db.add(admin)
        await db.flush()

        # Demo doctor
        doctor_user = User(
            email="doctor@gesturemed.ai",
            hashed_password=hash_password("Doctor123!"),
            full_name="Dr. Sarah Chen",
            role=UserRole.DOCTOR,
            is_verified=True,
        )
        db.add(doctor_user)
        await db.flush()
        db.add(DoctorProfile(
            user_id=doctor_user.id,
            specialization="General Medicine",
            hospital="GestureMed Demo Hospital",
            years_of_experience=8,
            bio="Demo doctor account for testing.",
            is_verified=True,
            available=True,
        ))

        # Demo patient
        patient_user = User(
            email="patient@gesturemed.ai",
            hashed_password=hash_password("Patient123!"),
            full_name="Alex Johnson",
            role=UserRole.PATIENT,
            is_verified=True,
        )
        db.add(patient_user)
        await db.flush()
        db.add(PatientProfile(
            user_id=patient_user.id,
            gender="non-binary",
            blood_type="O+",
            allergies=["Penicillin"],
            current_medications=["Lisinopril 10mg"],
        ))

        await db.commit()
        print("  ✅ Admin: admin@gesturemed.ai / Admin123!")
        print("  ✅ Doctor: doctor@gesturemed.ai / Doctor123!")
        print("  ✅ Patient: patient@gesturemed.ai / Patient123!")

asyncio.run(seed())
PYEOF
fi

echo ""
echo "🎉 Database initialisation complete!"
echo ""
echo "You can now access:"
echo "  Frontend:  http://localhost:3000"
echo "  API Docs:  http://localhost:8000/api/docs"
echo "  Health:    http://localhost:8000/health"
