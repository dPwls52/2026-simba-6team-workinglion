from django.db import models
from django.contrib.auth.models import User
from PIL import Image

class Pot(models.Model):
    host = models.ForeignKey(User, null=False, blank=False, on_delete=models.CASCADE)
    pot_name = models.CharField(max_length=100)
    days = models.IntegerField()
    fee = models.IntegerField()
    total_prize = models.IntegerField()
    pot_people = models.IntegerField()
    participants = models.ManyToManyField(User, related_name='join_pots', blank=True)
    pot_code = models.CharField(max_length=6, null=True, blank=True)


class Proof(models.Model):
    pot = models.ForeignKey(Pot, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='proof_images/')
    auth_date = models.DateField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image:
            image = Image.open(self.image.path)
            
            max_size = (800, 800) 
            
            image.thumbnail(max_size)
            image.save(self.image.path)


class PotAvatar(models.Model):
    pot = models.ForeignKey(Pot, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    color = models.CharField(max_length=20)
    item = models.CharField(max_length=20, null=True, blank=True)
