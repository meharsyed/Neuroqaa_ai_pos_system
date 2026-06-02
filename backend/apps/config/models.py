from django.db import models


class Setting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(default="")
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} = {self.value[:60]}"