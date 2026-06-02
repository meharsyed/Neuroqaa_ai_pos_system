from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SaleViewSet, ShiftViewSet, report_daily, report_date_range, report_inventory

router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")
router.register("shifts", ShiftViewSet, basename="shift")

urlpatterns = router.urls + [
    path("reports/daily/", report_daily, name="report-daily"),
    path("reports/date-range/", report_date_range, name="report-date-range"),
    path("reports/inventory/", report_inventory, name="report-inventory"),
]
