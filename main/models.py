from django.db import models
from django.contrib.auth.models import User

class Pot(models.Model):
    host = models.ForeignKey(User, null=False, blank=False, on_delete=models.CASCADE)
    pot_name = models.CharField(max_length=100)
    days = models.IntegerField()
    fee = models.IntegerField()
    total_prize = models.IntegerField()
    pot_people = models.IntegerField()
    participants = models.ManyToManyField(User, related_name='join_pots', blank=True)
    