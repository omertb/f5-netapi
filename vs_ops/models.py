from django.db import models


class LoadBalancer(models.Model):
    name = models.CharField(max_length=64, unique=True)
    ip_addr = models.CharField(max_length=64, null=True, unique=True)

    def __str__(self):
        return self.name

class Member(models.Model):
    name = models.CharField(max_length=64)
    ip_addr = models.CharField(max_length=64, null=True)
    port = models.CharField(max_length=5, null=True)
    pool_name = models.CharField(max_length=64)
    lb = models.ForeignKey(LoadBalancer, on_delete=models.CASCADE)
    state = models.CharField(max_length=16)
    monitor = models.CharField(max_length=32)
    session = models.CharField(max_length=32)

    class Meta:
        unique_together = (("name", "pool_name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.pool_name} - {self.lb}"


class Pool(models.Model):
    name = models.CharField(max_length=64)
    lb = models.ForeignKey(LoadBalancer, on_delete=models.CASCADE)
    member = models.ManyToManyField(Member, blank=True, related_name="members")
    lb_method = models.CharField(max_length=64)
    monitor = models.CharField(max_length=64)

    class Meta:
        unique_together = (("name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.lb}"


class IRule(models.Model):
    name = models.CharField(max_length=64)
    lb = models.ForeignKey(LoadBalancer, null=True, on_delete=models.CASCADE)
    content = models.CharField(max_length=65535, null=True)

    class Meta:
        unique_together = (("name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.lb}"


class Policy(models.Model):
    name = models.CharField(max_length=64)
    lb = models.ForeignKey(LoadBalancer, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.lb}"


class Profile(models.Model):
    name = models.CharField(max_length=64)
    lb = models.ForeignKey(LoadBalancer, on_delete=models.CASCADE)
    context = models.CharField(max_length=32, null=True)

    class Meta:
        unique_together = (("name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.lb}"


class VServer(models.Model):
    name = models.CharField(max_length=64)
    ip_addr = models.CharField(max_length=64, null=True)
    port =models.CharField(max_length=5, null=True)
    nat = models.CharField(max_length=32)
    persistence = models.CharField(max_length=32)
    lb = models.ForeignKey(LoadBalancer, on_delete=models.CASCADE)
    pool = models.ForeignKey(Pool, null=True, on_delete=models.SET_NULL)
    irule = models.ManyToManyField(IRule, blank=True, related_name="irules")
    policy = models.ManyToManyField(Policy, blank=True, related_name="policies")
    profile = models.ManyToManyField(Profile, blank=True, related_name="profiles")

    class Meta:
        unique_together = (("name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.lb}"