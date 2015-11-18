from django.db import models

class Url_Note(models.Model):
    url = models.CharField(max_length=250)
    note = models.CharField(max_length=1000)
    user = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

class Sections_Scraping(models.Model):
    url = models.CharField(max_length=250)
    sections_scraping = models.CharField(max_length=5000)
    timestamp = models.DateTimeField(auto_now_add=True)
