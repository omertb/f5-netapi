from django.db import models


class LoadBalancer(models.Model):
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name

class Member(models.Model):
    name = models.CharField(max_length=64)
    pool_name = models.CharField(max_length=64)
    lb = models.ForeignKey(LoadBalancer, on_delete=models.DO_NOTHING)
    state = models.CharField(max_length=16)
    monitor = models.CharField(max_length=32)
    session = models.CharField(max_length=32)

    class Meta:
        unique_together = (("name", "pool_name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.pool_name} - {self.lb}"


class Pool(models.Model):
    name = models.CharField(max_length=64)
    lb = models.ForeignKey(LoadBalancer, on_delete=models.DO_NOTHING)
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING)
    lb_method = models.CharField(max_length=64)
    monitor = models.CharField(max_length=64)

    class Meta:
        unique_together = (("name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.lb}"


class IRule(models.Model):
    name = models.CharField(max_length=64)
    lb = models.ForeignKey(LoadBalancer, null=True, on_delete=models.DO_NOTHING)
    content = models.CharField(max_length=65535, null=True)

    class Meta:
        unique_together = (("name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.lb}"


class Policy(models.Model):
    name = models.CharField(max_length=64)
    lb = models.ForeignKey(LoadBalancer, on_delete=models.DO_NOTHING)

    class Meta:
        unique_together = (("name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.lb}"


class Profile(models.Model):
    name = models.CharField(max_length=64)
    lb = models.ForeignKey(LoadBalancer, on_delete=models.DO_NOTHING)

    class Meta:
        unique_together = (("name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.lb}"


class VServer(models.Model):
    name = models.CharField(max_length=64)
    ip_addr_port = models.CharField(max_length=64)
    nat = models.CharField(max_length=32)
    persistence = models.CharField(max_length=32)
    lb = models.ForeignKey(LoadBalancer, on_delete=models.DO_NOTHING)
    pool = models.ForeignKey(Pool, null=True, on_delete=models.DO_NOTHING)
    irule = models.ManyToManyField(IRule, blank=True, related_name="irules")
    policy = models.ManyToManyField(Policy, blank=True, related_name="policies")
    profile = models.ManyToManyField(Profile, blank=True, related_name="profiles")

    class Meta:
        unique_together = (("name", "lb"),)

    def __str__(self):
        return f"{self.name} - {self.lb}"