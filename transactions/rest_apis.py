import json

from django.contrib.auth.models import User

from rest_framework.response import Response
from rest_framework.views import APIView

from . models import *
from . import ardor_access
from usermgmt.models import APIAccessKey, UserDetails

class RegisterTransaction(APIView):

    def get(self, request, format=None):
        return Response({"Message": "Try the POST request, GET request can\'t be done on this API"})


    def post(self, request, format=None):
        data = request.data
        api_key = data['key']
        try:
            try:
                accessKey = APIAccessKey.objects.get(key = api_key)
            except:
                return Response({"transaction_status": "invalid key error"})
            seller = accessKey.user

            tr = Transaction()
            tr.seller = seller
            tr.apikey = accessKey
            try:
                tr.customer = User.objects.get(email=data['customer_email'])
            except:
                return Response({"transaction_status": "customer not found"})
            tr.amount = data['amount']
            tr.save()

            tr.checkout_code = ("".join(tr.apikey.name.split(" ")))+'-'+str(tr.id)
            tr.save()

            # TODO: add sushranth's functions to get tr.transaction_res (Transaction json)
            seller_det = UserDetails.objects.get(user = seller)
            customer_det = UserDetails.objects.get(user = tr.customer)

            transactionJSON = ardor_access.get_unsigned_transaction_bytes(receiver_account_id=seller_det.ardor_acc_num, sender_public_key=customer_det.ardor_public_key, payment_amount=data['amount'])
            transactionJSON_str = json.dumps(transactionJSON)
            tr.transaction_res = transactionJSON_str
            tr.save()

            return Response({"transaction_status": "registered", "id": tr.id, "checkout_code": tr.checkout_code})

        except:
            return Response({"transaction_status": "error"})

class ConfirmTransaction(APIView):
    def get(self, request, format=None):
        return Response({"Message": "Try the POST request, GET request can\'t be done on this API"})

    def post(self, request, format=None):
        data = request.data
        try:
            try:
                checkout_code = data['checkout_code']
                tr = Transaction.objects.get(checkout_code=checkout_code)
            except:
                return Response({"transaction_status": "invalid checkout_code"})

            passphrase = data['passphrase']

            status = False

            try:
                status = ardor_access.confirm_transaction(unsignedTransactionJSON=json.loads(tr.transaction_res), secret_pass_phrase=passphrase)
            except:
                return Response({"transaction_status": "error on the ardor side"})

            if(status == True):
                tr.completed = True
                tr.save()

                return Response({"transaction_status": "executed"})

            else:
                return Response({"transaction_status": "failed"})

        except:
            return Response({"transaction_status": "error"})
