"""
Management Command: seed_data

Creates sample employees, leave requests, payroll records,
and per-category leave balances for testing and demonstration.

Usage:
    python manage.py seed_data
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.authentication.models import Employee
from apps.hr_queries.models import LeaveRequest, Payroll, LeaveBalance


class Command(BaseCommand):
    help = "Seed the database with sample HR data for testing."

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding database...\n")

        # ---- Sample Employees ----
        employees_data = [
            {
                "employee_id": "EMP001",
                "name": "Harsha Lakshmi M",
                "department": "Engineering",
                "email": "harsha@company.com",
                "password": "password123",
                "leave_balance": 18,
                "attendance_percentage": 94.50,
            },
            {
                "employee_id": "EMP002",
                "name": "Dharshini VP",
                "department": "Marketing",
                "email": "dharshini@company.com",
                "password": "password123",
                "leave_balance": 12,
                "attendance_percentage": 97.00,
            },
            {
                "employee_id": "EMP003",
                "name": "Mokitha W",
                "department": "Finance",
                "email": "mokitha@company.com",
                "password": "password123",
                "leave_balance": 20,
                "attendance_percentage": 88.75,
            },
            {
                "employee_id": "EMP004",
                "name": "Sachin Saghar PT",
                "department": "Human Resources",
                "email": "sachin@company.com",
                "password": "password123",
                "leave_balance": 5,
                "attendance_percentage": 99.00,
            },
            {
                "employee_id": "EMP005",
                "name": "Vishnu",
                "department": "Engineering",
                "email": "vishnu@company.com",
                "password": "password123",
                "leave_balance": 15,
                "attendance_percentage": 91.25,
            },
            {
                "employee_id": "HR001",
                "name": "Gopi",
                "department": "HR Management",
                "email": "gopi@company.com",
                "password": "password123",
                "leave_balance": 25,
                "attendance_percentage": 100.00,
                "is_hr": True,
            },
        ]

        created_employees = []
        for emp_data in employees_data:
            password = emp_data.pop("password")
            emp, created = Employee.objects.get_or_create(
                employee_id=emp_data["employee_id"],
                defaults=emp_data,
            )
            if created:
                emp.set_password(password)
                emp.save()
                self.stdout.write(f"  ✅ Created employee: {emp}")
            else:
                self.stdout.write(f"  ⏭️  Employee already exists: {emp}")
            created_employees.append(emp)

        # ---- Per-Category Leave Balances ----
        default_quotas = [("casual", 12), ("medical", 10), ("earned", 15)]
        for emp in created_employees:
            for lt, total in default_quotas:
                obj, created = LeaveBalance.objects.get_or_create(
                    employee=emp, leave_type=lt,
                    defaults={"total": total, "used": 0},
                )
                if created:
                    self.stdout.write(f"  ✅ LeaveBalance: {obj}")

        # ---- Sample Leave Requests ----
        today = date.today()
        leave_data = [
            {
                "employee": created_employees[0],
                "leave_type": "casual",
                "start_date": today - timedelta(days=10),
                "end_date": today - timedelta(days=8),
                "reason": "Family function",
                "status": "approved",
            },
            {
                "employee": created_employees[0],
                "leave_type": "medical",
                "start_date": today + timedelta(days=5),
                "end_date": today + timedelta(days=6),
                "reason": "Doctor appointment",
                "status": "pending",
            },
            {
                "employee": created_employees[1],
                "leave_type": "medical",
                "start_date": today - timedelta(days=3),
                "end_date": today - timedelta(days=1),
                "reason": "Medical appointment",
                "status": "approved",
            },
            {
                "employee": created_employees[2],
                "leave_type": "earned",
                "start_date": today + timedelta(days=10),
                "end_date": today + timedelta(days=15),
                "reason": "Vacation",
                "status": "pending",
            },
        ]

        for leave in leave_data:
            obj, created = LeaveRequest.objects.get_or_create(
                employee=leave["employee"],
                start_date=leave["start_date"],
                end_date=leave["end_date"],
                defaults={
                    "leave_type": leave["leave_type"],
                    "reason": leave["reason"],
                    "status": leave["status"],
                },
            )
            if created:
                self.stdout.write(f"  ✅ Leave request: {obj}")
            else:
                self.stdout.write(f"  ⏭️  Leave already exists: {obj}")

        # ---- Sample Payroll Records ----
        payroll_data = [
            {"employee": created_employees[0], "salary": 85000.00, "bonus": 10000.00, "last_paid_date": today - timedelta(days=5)},
            {"employee": created_employees[1], "salary": 72000.00, "bonus": 8000.00, "last_paid_date": today - timedelta(days=5)},
            {"employee": created_employees[2], "salary": 95000.00, "bonus": 15000.00, "last_paid_date": today - timedelta(days=5)},
            {"employee": created_employees[3], "salary": 68000.00, "bonus": 5000.00, "last_paid_date": today - timedelta(days=5)},
            {"employee": created_employees[4], "salary": 90000.00, "bonus": 12000.00, "last_paid_date": today - timedelta(days=5)},
            {"employee": created_employees[5], "salary": 110000.00, "bonus": 20000.00, "last_paid_date": today - timedelta(days=5)},
        ]

        for pay in payroll_data:
            obj, created = Payroll.objects.get_or_create(
                employee=pay["employee"],
                defaults={
                    "salary": pay["salary"],
                    "bonus": pay["bonus"],
                    "last_paid_date": pay["last_paid_date"],
                },
            )
            if created:
                self.stdout.write(f"  ✅ Payroll: {obj}")
            else:
                self.stdout.write(f"  ⏭️  Payroll already exists: {obj}")

        self.stdout.write(self.style.SUCCESS("\n✨ Seed data complete!"))
        self.stdout.write("\n📋 Test Credentials (Employee):")
        self.stdout.write("   Employee ID: EMP001")
        self.stdout.write("   Password:    password123\n")
        self.stdout.write("📋 Test Credentials (HR Admin):")
        self.stdout.write("   Employee ID: HR001")
        self.stdout.write("   Password:    password123\n")
