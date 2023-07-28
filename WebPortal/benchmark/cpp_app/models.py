from django.db import models

class Benchmark(models.Model):
    identifier = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    csv_file = models.FileField(upload_to='csv_files/')
