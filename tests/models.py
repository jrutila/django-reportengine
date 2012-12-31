from django.db import models



class Address(models.Model):
    street = models.TextField()
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=2)
    postal_code = models.CharField(max_length=10)
    customer = models.ForeignKey("Customer", related_name='shipping_addresses')

class PaymentInfo(models.Model):
    #TODO - Not really real.  This will be randomly generated by
    # factory_boy
    payment_token = models.CharField(max_length=16)

class BillingInfo(models.Model):
    address = models.ForeignKey(Address)
    payment_info = models.ForeignKey(PaymentInfo)

class Customer(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    stamp = models.DateTimeField()
    age = models.IntegerField()


class Sale(models.Model):
    customer = models.ForeignKey(Customer)
    ship_address = models.ForeignKey(Address)
    bill_info = models.ForeignKey(BillingInfo)

    purchase_date = models.DateTimeField()

    total = models.DecimalField(max_digits=6,decimal_places=2)
    tax_rate = models.DecimalField(max_digits=4, decimal_places=2)


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale)

    department = models.CharField(max_length=20)
    classification = models.CharField(max_length=20)
    sub_classification = models.CharField(max_length=20)
    name = models.CharField(max_length=64)
    price = models.DecimalField(max_digits=10,decimal_places=2)
    option1 = models.CharField(max_length=64)
    option2 = models.CharField(max_length=64)
