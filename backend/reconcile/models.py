from django.db import models


class Location(models.Model):
    """
    Authoritative mapping of location to organization (tenant).
    Never infer organization from location ID patterns.
    """
    location_id = models.CharField(max_length=64, unique=True, db_index=True)
    org_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.location_id} ({self.org_id})"


class SystemARecord(models.Model):
    """
    Represents an event recorded in System A.
    """
    record_id = models.CharField(max_length=64, unique=True, db_index=True)
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_a_records'
    )
    location_id_raw = models.CharField(max_length=255, null=True, blank=True)
    event_date = models.DateField(null=True, blank=True)
    event_date_raw = models.CharField(max_length=255, null=True, blank=True)
    category_code = models.CharField(max_length=64, null=True, blank=True)
    actor_id = models.CharField(max_length=64, null=True, blank=True)
    base_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    base_value_raw = models.CharField(max_length=255, null=True, blank=True)
    adjustment = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    adjustment_raw = models.CharField(max_length=255, null=True, blank=True)
    total_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    total_value_raw = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=64, default='CONFIRMED')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SystemARecord {self.record_id} [{self.state}]"


class SystemBEntry(models.Model):
    """
    Represents an entry recorded in System B.
    Points back to System A via normalized record_ref (NOT a foreign key).
    Multiple B entries can reference the same A record, and orphan entries must be preserved.
    """
    entry_id = models.CharField(max_length=64, unique=True, db_index=True)
    record_ref_raw = models.CharField(max_length=255, null=True, blank=True)
    record_ref = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_b_entries'
    )
    location_id_raw = models.CharField(max_length=255, null=True, blank=True)
    recorded_on = models.DateField(null=True, blank=True)
    recorded_on_raw = models.CharField(max_length=255, null=True, blank=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    value_raw = models.CharField(max_length=255, null=True, blank=True)
    label = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SystemBEntry {self.entry_id} -> {self.record_ref}"
