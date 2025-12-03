"""
Payment processing services for PayPal, MTN MoMo, and Bank Transfer
"""
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import requests
import logging
import uuid

logger = logging.getLogger(__name__)


class PaymentException(Exception):
    """Base exception for payment processing"""
    pass


class PayPalPaymentService:
    """
    PayPal payment integration service
    Uses PayPal REST API v2
    """

    def __init__(self):
        self.client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', '')
        self.mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')  # sandbox or live

        if self.mode == 'sandbox':
            self.base_url = 'https://api-m.sandbox.paypal.com'
        else:
            self.base_url = 'https://api-m.paypal.com'

    def get_access_token(self):
        """Get PayPal OAuth access token"""
        url = f"{self.base_url}/v1/oauth2/token"

        headers = {
            'Accept': 'application/json',
            'Accept-Language': 'en_US',
        }

        data = {
            'grant_type': 'client_credentials'
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                auth=(self.client_id, self.client_secret),
                timeout=30
            )
            response.raise_for_status()
            return response.json()['access_token']
        except Exception as e:
            logger.error(f"PayPal auth error: {str(e)}")
            raise PaymentException(f"Erreur d'authentification PayPal: {str(e)}")

    def create_order(self, order, return_url, cancel_url):
        """
        Create PayPal order for payment

        Args:
            order: Order model instance
            return_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled

        Returns:
            dict: PayPal order response with approval URL
        """
        access_token = self.get_access_token()
        url = f"{self.base_url}/v2/checkout/orders"

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }

        # Convert XAF to USD (approximate rate: 1 USD = 600 XAF)
        # In production, use a real currency conversion API
        amount_usd = float(order.total_amount) / 600

        payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': order.order_number,
                'description': f'{order.plan.display_name} - {order.billing_cycle}',
                'amount': {
                    'currency_code': 'USD',
                    'value': f'{amount_usd:.2f}'
                },
                'custom_id': str(order.id)
            }],
            'application_context': {
                'brand_name': 'ESXi Backup Manager',
                'landing_page': 'BILLING',
                'user_action': 'PAY_NOW',
                'return_url': return_url,
                'cancel_url': cancel_url
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            paypal_order = response.json()

            # Extract approval URL
            approval_url = None
            for link in paypal_order.get('links', []):
                if link['rel'] == 'approve':
                    approval_url = link['href']
                    break

            return {
                'paypal_order_id': paypal_order['id'],
                'status': paypal_order['status'],
                'approval_url': approval_url
            }

        except Exception as e:
            logger.error(f"PayPal create order error: {str(e)}")
            raise PaymentException(f"Erreur lors de la création de la commande PayPal: {str(e)}")

    def capture_payment(self, paypal_order_id):
        """
        Capture payment after user approval

        Args:
            paypal_order_id: PayPal order ID

        Returns:
            dict: Payment capture details
        """
        access_token = self.get_access_token()
        url = f"{self.base_url}/v2/checkout/orders/{paypal_order_id}/capture"

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }

        try:
            response = requests.post(url, headers=headers, timeout=30)
            response.raise_for_status()

            capture_result = response.json()

            # Extract capture details
            capture = capture_result['purchase_units'][0]['payments']['captures'][0]

            return {
                'status': capture['status'],  # COMPLETED, PENDING, etc.
                'transaction_id': capture['id'],
                'amount': capture['amount']['value'],
                'currency': capture['amount']['currency_code'],
                'custom_id': capture_result['purchase_units'][0].get('custom_id'),
                'raw_response': capture_result
            }

        except Exception as e:
            logger.error(f"PayPal capture error: {str(e)}")
            raise PaymentException(f"Erreur lors de la capture du paiement PayPal: {str(e)}")

    def verify_webhook(self, webhook_id, headers, body):
        """
        Verify PayPal webhook signature

        Args:
            webhook_id: PayPal webhook ID
            headers: Request headers
            body: Request body

        Returns:
            bool: True if webhook is valid
        """
        access_token = self.get_access_token()
        url = f"{self.base_url}/v1/notifications/verify-webhook-signature"

        request_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }

        payload = {
            'transmission_id': headers.get('PAYPAL-TRANSMISSION-ID'),
            'transmission_time': headers.get('PAYPAL-TRANSMISSION-TIME'),
            'cert_url': headers.get('PAYPAL-CERT-URL'),
            'auth_algo': headers.get('PAYPAL-AUTH-ALGO'),
            'transmission_sig': headers.get('PAYPAL-TRANSMISSION-SIG'),
            'webhook_id': webhook_id,
            'webhook_event': body
        }

        try:
            response = requests.post(url, json=payload, headers=request_headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result.get('verification_status') == 'SUCCESS'
        except Exception as e:
            logger.error(f"PayPal webhook verification error: {str(e)}")
            return False


class MTNMoMoPaymentService:
    """
    MTN Mobile Money payment integration service
    Uses MTN MoMo Collections API
    """

    def __init__(self):
        self.subscription_key = getattr(settings, 'MTN_MOMO_SUBSCRIPTION_KEY', '')
        self.user_id = getattr(settings, 'MTN_MOMO_USER_ID', '')
        self.api_key = getattr(settings, 'MTN_MOMO_API_KEY', '')
        self.environment = getattr(settings, 'MTN_MOMO_ENVIRONMENT', 'sandbox')  # sandbox or production

        if self.environment == 'sandbox':
            self.base_url = 'https://sandbox.momodeveloper.mtn.com'
        else:
            self.base_url = 'https://momodeveloper.mtn.com'

    def create_access_token(self):
        """Create MTN MoMo access token"""
        url = f"{self.base_url}/collection/token/"

        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Authorization': f'Basic {self.api_key}'
        }

        try:
            response = requests.post(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()['access_token']
        except Exception as e:
            logger.error(f"MTN MoMo auth error: {str(e)}")
            raise PaymentException(f"Erreur d'authentification MTN MoMo: {str(e)}")

    def request_to_pay(self, order, phone_number):
        """
        Request payment from customer

        Args:
            order: Order model instance
            phone_number: Customer phone number in format: 237XXXXXXXXX

        Returns:
            dict: Payment request details with reference ID
        """
        access_token = self.create_access_token()
        reference_id = str(uuid.uuid4())

        url = f"{self.base_url}/collection/v1_0/requesttopay"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Reference-Id': reference_id,
            'X-Target-Environment': self.environment,
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json'
        }

        payload = {
            'amount': str(int(order.total_amount)),  # Amount in XAF, no decimals
            'currency': 'XAF',
            'externalId': order.order_number,
            'payer': {
                'partyIdType': 'MSISDN',
                'partyId': phone_number
            },
            'payerMessage': f'Paiement {order.plan.display_name}',
            'payeeNote': f'ESXi Backup Manager - Order {order.order_number}'
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            return {
                'reference_id': reference_id,
                'status': 'PENDING',
                'external_id': order.order_number
            }

        except Exception as e:
            logger.error(f"MTN MoMo request to pay error: {str(e)}")
            raise PaymentException(f"Erreur lors de la demande de paiement MTN MoMo: {str(e)}")

    def get_transaction_status(self, reference_id):
        """
        Check payment status

        Args:
            reference_id: Reference ID from request_to_pay

        Returns:
            dict: Transaction status details
        """
        access_token = self.create_access_token()

        url = f"{self.base_url}/collection/v1_0/requesttopay/{reference_id}"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Target-Environment': self.environment,
            'Ocp-Apim-Subscription-Key': self.subscription_key
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()

            return {
                'status': result['status'],  # SUCCESSFUL, PENDING, FAILED
                'amount': result['amount'],
                'currency': result['currency'],
                'external_id': result.get('externalId'),
                'payer': result.get('payer', {}),
                'reason': result.get('reason'),
                'raw_response': result
            }

        except Exception as e:
            logger.error(f"MTN MoMo status check error: {str(e)}")
            raise PaymentException(f"Erreur lors de la vérification du statut: {str(e)}")


class BankTransferPaymentService:
    """
    Bank transfer payment service (manual verification)
    """

    @staticmethod
    def get_bank_details():
        """Get company bank account details for transfer"""
        return {
            'bank_name': getattr(settings, 'BANK_NAME', 'Votre Banque'),
            'account_name': getattr(settings, 'BANK_ACCOUNT_NAME', 'ESXi Backup Manager SAS'),
            'account_number': getattr(settings, 'BANK_ACCOUNT_NUMBER', 'XXXXXXXXXXXX'),
            'swift_code': getattr(settings, 'BANK_SWIFT_CODE', 'XXXXXXXX'),
            'iban': getattr(settings, 'BANK_IBAN', 'XX XX XXXX XXXX XXXX XXXX XXXX XXX'),
            'branch': getattr(settings, 'BANK_BRANCH', 'Agence Principale'),
            'currency': 'XAF'
        }

    @staticmethod
    def create_bank_transfer_reference(order):
        """
        Generate unique reference for bank transfer

        Args:
            order: Order model instance

        Returns:
            str: Unique reference to include in transfer description
        """
        return f"ESXI-{order.order_number}"

    @staticmethod
    def verify_bank_transfer(payment, admin_user):
        """
        Manually verify bank transfer by admin

        Args:
            payment: Payment model instance
            admin_user: User performing verification

        Returns:
            bool: Verification success
        """
        from ..models import Payment

        try:
            payment.status = 'completed'
            payment.verified_by = admin_user
            payment.verified_at = timezone.now()
            payment.completed_at = timezone.now()
            payment.save()

            logger.info(f"Bank transfer {payment.transaction_id} verified by {admin_user.username}")
            return True

        except Exception as e:
            logger.error(f"Bank transfer verification error: {str(e)}")
            return False


class PaymentService:
    """
    Main payment service orchestrator
    Routes payment requests to appropriate payment provider
    """

    def __init__(self):
        self.paypal = PayPalPaymentService()
        self.mtn_momo = MTNMoMoPaymentService()
        self.bank_transfer = BankTransferPaymentService()

    def initiate_payment(self, order, payment_method, **kwargs):
        """
        Initiate payment for an order

        Args:
            order: Order model instance
            payment_method: PaymentMethod model instance
            **kwargs: Additional parameters (phone_number for MTN, URLs for PayPal, etc.)

        Returns:
            dict: Payment initiation response
        """
        from ..models import Payment

        method_name = payment_method.name

        try:
            if method_name == 'paypal':
                # PayPal payment
                return_url = kwargs.get('return_url')
                cancel_url = kwargs.get('cancel_url')

                result = self.paypal.create_order(order, return_url, cancel_url)

                # Create Payment record
                payment = Payment.objects.create(
                    transaction_id=f"PP-{result['paypal_order_id']}",
                    order=order,
                    organization=order.organization,
                    payment_method=payment_method,
                    amount=order.total_amount,
                    currency=order.currency,
                    status='pending',
                    provider_transaction_id=result['paypal_order_id'],
                    provider_response=result
                )

                return {
                    'success': True,
                    'payment_id': payment.id,
                    'redirect_url': result['approval_url'],
                    'method': 'paypal'
                }

            elif method_name == 'mtn_momo':
                # MTN Mobile Money
                phone_number = kwargs.get('phone_number')
                if not phone_number:
                    raise PaymentException("Numéro de téléphone requis pour MTN MoMo")

                result = self.mtn_momo.request_to_pay(order, phone_number)

                # Create Payment record
                payment = Payment.objects.create(
                    transaction_id=f"MTN-{result['reference_id']}",
                    order=order,
                    organization=order.organization,
                    payment_method=payment_method,
                    amount=order.total_amount,
                    currency='XAF',
                    status='pending',
                    provider_transaction_id=result['reference_id'],
                    provider_response=result
                )

                return {
                    'success': True,
                    'payment_id': payment.id,
                    'reference_id': result['reference_id'],
                    'status': 'pending',
                    'message': 'Vérifiez votre téléphone pour confirmer le paiement',
                    'method': 'mtn_momo'
                }

            elif method_name == 'bank_transfer':
                # Bank transfer
                bank_details = self.bank_transfer.get_bank_details()
                reference = self.bank_transfer.create_bank_transfer_reference(order)

                # Create Payment record
                payment = Payment.objects.create(
                    transaction_id=f"BT-{reference}",
                    order=order,
                    organization=order.organization,
                    payment_method=payment_method,
                    amount=order.total_amount,
                    currency='XAF',
                    status='pending',
                    bank_reference=reference
                )

                return {
                    'success': True,
                    'payment_id': payment.id,
                    'bank_details': bank_details,
                    'reference': reference,
                    'message': 'Effectuez le virement et téléchargez le reçu',
                    'method': 'bank_transfer'
                }

            else:
                raise PaymentException(f"Méthode de paiement non supportée: {method_name}")

        except PaymentException as e:
            logger.error(f"Payment initiation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected payment error: {str(e)}")
            raise PaymentException(f"Erreur inattendue lors du paiement: {str(e)}")

    def verify_payment(self, payment):
        """
        Verify payment status

        Args:
            payment: Payment model instance

        Returns:
            dict: Payment verification result
        """
        method_name = payment.payment_method.name

        try:
            if method_name == 'paypal':
                # PayPal verification
                paypal_order_id = payment.provider_transaction_id
                result = self.paypal.capture_payment(paypal_order_id)

                if result['status'] == 'COMPLETED':
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.provider_response = result['raw_response']
                    payment.save()

                    return {'success': True, 'status': 'completed'}
                else:
                    return {'success': False, 'status': result['status']}

            elif method_name == 'mtn_momo':
                # MTN MoMo verification
                reference_id = payment.provider_transaction_id
                result = self.mtn_momo.get_transaction_status(reference_id)

                if result['status'] == 'SUCCESSFUL':
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.provider_response = result['raw_response']
                    payment.save()

                    return {'success': True, 'status': 'completed'}
                elif result['status'] == 'FAILED':
                    payment.status = 'failed'
                    payment.error_message = result.get('reason', 'Payment failed')
                    payment.save()

                    return {'success': False, 'status': 'failed'}
                else:
                    return {'success': False, 'status': 'pending'}

            elif method_name == 'bank_transfer':
                # Bank transfer requires manual verification
                return {
                    'success': False,
                    'status': payment.status,
                    'message': 'Vérification manuelle requise par un administrateur'
                }

        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return {'success': False, 'error': str(e)}
