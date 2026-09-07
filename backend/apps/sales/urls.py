from django.urls import path
from rest_framework.routers import DefaultRouter

from .quotation_views import BusinessProfileViewSet, QuotationViewSet
from .views import SaleViewSet, ShiftViewSet, report_audit, report_daily, report_inventory

router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")
router.register("shifts", ShiftViewSet, basename="shift")
router.register("quotations", QuotationViewSet, basename="quotation")
router.register("business-profiles", BusinessProfileViewSet, basename="business-profile")

urlpatterns = router.urls + [
    path("reports/daily/", report_daily, name="report-daily"),
    path("reports/inventory/", report_inventory, name="report-inventory"),
    path("reports/audit/", report_audit, name="report-audit"),
]
