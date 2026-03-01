"""
Stripe Payment Processing Service

Handles one-time payments, subscriptions, and billing for SETTLE.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class StripeService:
    """
    Service for processing payments via Stripe.
    
    Pricing:
    - Founding Members: Free forever (first 2,100)
    - Standard Users: $49 per report
    - Premium Subscription: $199/month unlimited
    - Enterprise: Custom pricing
    """
    
    def __init__(self):
        """Initialize Stripe service with API keys."""
        self.secret_key = os.getenv("SETTLE_STRIPE_SECRET_KEY")
        self.publishable_key = os.getenv("SETTLE_STRIPE_PUBLISHABLE_KEY")
        self.webhook_secret = os.getenv("SETTLE_STRIPE_WEBHOOK_SECRET")
        
        self.enabled = bool(self.secret_key)
        
        if not self.enabled:
            logger.warning("Stripe API key not configured. Payments will be mocked.")
        else:
            self._initialize_stripe()
    
    def _initialize_stripe(self):
        """Initialize Stripe library."""
        try:
            import stripe
            stripe.api_key = self.secret_key
            self.stripe = stripe
            logger.info("Stripe client initialized")
        except ImportError:
            logger.error("stripe library not installed. Payment functionality disabled.")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Stripe: {str(e)}", exc_info=True)
            self.enabled = False
    
    async def create_customer(
        self,
        email: str,
        name: str,
        user_id: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Create a Stripe customer.
        
        Args:
            email: Customer email
            name: Customer name
            user_id: Internal user ID
            metadata: Optional metadata
            
        Returns:
            Stripe customer ID
        """
        if not self.enabled:
            logger.info(f"[MOCK] Create Stripe customer: {email}")
            return f"cus_mock_{user_id}"
        
        try:
            customer_metadata = metadata or {}
            customer_metadata['user_id'] = user_id
            
            customer = self.stripe.Customer.create(
                email=email,
                name=name,
                metadata=customer_metadata
            )
            
            logger.info(f"Stripe customer created: {customer.id}")
            return customer.id
            
        except Exception as e:
            logger.error(f"Failed to create Stripe customer: {str(e)}", exc_info=True)
            return None
    
    async def create_payment_intent(
        self,
        amount_cents: int,
        customer_id: str,
        report_id: str,
        description: str = "SETTLE Settlement Report"
    ) -> Optional[Dict[str, Any]]:
        """
        Create a payment intent for a one-time report purchase.
        
        Args:
            amount_cents: Amount in cents (e.g., 4900 for $49)
            customer_id: Stripe customer ID
            report_id: Report UUID
            description: Payment description
            
        Returns:
            Payment intent dictionary
        """
        if not self.enabled:
            logger.info(f"[MOCK] Create payment intent: ${amount_cents/100:.2f}")
            return {
                "id": f"pi_mock_{report_id}",
                "client_secret": "mock_secret_xxx",
                "amount": amount_cents,
                "status": "succeeded"
            }
        
        try:
            intent = self.stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                customer=customer_id,
                description=description,
                metadata={
                    'report_id': report_id,
                    'product': 'settle_report'
                },
                automatic_payment_methods={'enabled': True}
            )
            
            logger.info(f"Payment intent created: {intent.id} (${amount_cents/100:.2f})")
            
            return {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "amount": intent.amount,
                "status": intent.status
            }
            
        except Exception as e:
            logger.error(f"Failed to create payment intent: {str(e)}", exc_info=True)
            return None
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_period_days: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a subscription for premium users.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID (e.g., premium $199/month)
            trial_period_days: Optional trial period
            
        Returns:
            Subscription dictionary
        """
        if not self.enabled:
            logger.info(f"[MOCK] Create subscription: {price_id}")
            return {
                "id": f"sub_mock_{customer_id}",
                "status": "active",
                "current_period_end": int(datetime.utcnow().timestamp()) + 2592000  # +30 days
            }
        
        try:
            subscription = self.stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                trial_period_days=trial_period_days,
                metadata={'product': 'settle_premium'}
            )
            
            logger.info(f"Subscription created: {subscription.id}")
            
            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
                "trial_end": subscription.trial_end
            }
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {str(e)}", exc_info=True)
            return None
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False
    ) -> bool:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            immediately: Cancel immediately vs. at period end
            
        Returns:
            True if cancelled successfully
        """
        if not self.enabled:
            logger.info(f"[MOCK] Cancel subscription: {subscription_id}")
            return True
        
        try:
            if immediately:
                self.stripe.Subscription.delete(subscription_id)
                logger.info(f"Subscription cancelled immediately: {subscription_id}")
            else:
                self.stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
                logger.info(f"Subscription set to cancel at period end: {subscription_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {str(e)}", exc_info=True)
            return False
    
    async def create_refund(
        self,
        payment_intent_id: str,
        amount_cents: Optional[int] = None,
        reason: str = "requested_by_customer"
    ) -> Optional[str]:
        """
        Process a refund.
        
        Args:
            payment_intent_id: Payment intent ID
            amount_cents: Amount to refund (None = full refund)
            reason: Refund reason
            
        Returns:
            Refund ID
        """
        if not self.enabled:
            logger.info(f"[MOCK] Create refund: {payment_intent_id}")
            return f"re_mock_{payment_intent_id}"
        
        try:
            refund_params = {
                'payment_intent': payment_intent_id,
                'reason': reason
            }
            
            if amount_cents:
                refund_params['amount'] = amount_cents
            
            refund = self.stripe.Refund.create(**refund_params)
            
            logger.info(f"Refund processed: {refund.id} (${refund.amount/100:.2f})")
            return refund.id
            
        except Exception as e:
            logger.error(f"Failed to process refund: {str(e)}", exc_info=True)
            return None
    
    async def get_customer_payment_methods(
        self,
        customer_id: str
    ) -> list:
        """
        Get payment methods for a customer.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            List of payment methods
        """
        if not self.enabled:
            logger.info(f"[MOCK] Get payment methods: {customer_id}")
            return [
                {
                    "id": "pm_mock_123",
                    "type": "card",
                    "card": {
                        "brand": "visa",
                        "last4": "4242",
                        "exp_month": 12,
                        "exp_year": 2025
                    }
                }
            ]
        
        try:
            payment_methods = self.stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            
            return [
                {
                    "id": pm.id,
                    "type": pm.type,
                    "card": {
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                        "exp_month": pm.card.exp_month,
                        "exp_year": pm.card.exp_year
                    }
                }
                for pm in payment_methods.data
            ]
            
        except Exception as e:
            logger.error(f"Failed to get payment methods: {str(e)}", exc_info=True)
            return []
    
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify Stripe webhook signature and parse event.
        
        Args:
            payload: Request body bytes
            signature: Stripe-Signature header value
            
        Returns:
            Stripe event dictionary
        """
        if not self.enabled or not self.webhook_secret:
            logger.warning("[MOCK] Webhook verification skipped")
            return {"type": "mock.event"}
        
        try:
            event = self.stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            logger.info(f"Webhook verified: {event['type']}")
            return event
            
        except Exception as e:
            logger.error(f"Webhook verification failed: {str(e)}", exc_info=True)
            return None
    
    async def handle_webhook_event(
        self,
        event: Dict[str, Any]
    ) -> bool:
        """
        Handle Stripe webhook events.
        
        Args:
            event: Stripe event dictionary
            
        Returns:
            True if handled successfully
        """
        event_type = event.get('type')
        
        try:
            if event_type == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                logger.info(f"Payment succeeded: {payment_intent['id']}")
                # TODO: Update database, send email notification
                
            elif event_type == 'payment_intent.payment_failed':
                payment_intent = event['data']['object']
                logger.warning(f"Payment failed: {payment_intent['id']}")
                # TODO: Send failure notification
                
            elif event_type == 'customer.subscription.created':
                subscription = event['data']['object']
                logger.info(f"Subscription created: {subscription['id']}")
                # TODO: Update user access level
                
            elif event_type == 'customer.subscription.deleted':
                subscription = event['data']['object']
                logger.info(f"Subscription cancelled: {subscription['id']}")
                # TODO: Downgrade user access
                
            elif event_type == 'invoice.payment_succeeded':
                invoice = event['data']['object']
                logger.info(f"Invoice paid: {invoice['id']}")
                # TODO: Send receipt
                
            elif event_type == 'invoice.payment_failed':
                invoice = event['data']['object']
                logger.warning(f"Invoice payment failed: {invoice['id']}")
                # TODO: Send payment failure notification
                
            else:
                logger.info(f"Unhandled webhook event: {event_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle webhook event: {str(e)}", exc_info=True)
            return False
    
    async def get_pricing(self) -> Dict[str, Any]:
        """
        Get current pricing information.
        
        Returns:
            Dictionary with pricing details
        """
        return {
            "founding_member": {
                "price": 0,
                "currency": "USD",
                "description": "Free forever (first 2,100 members)",
                "features": [
                    "Unlimited queries",
                    "Unlimited PDF reports",
                    "API access",
                    "Priority support",
                    "Early feature access"
                ]
            },
            "standard_report": {
                "price": 49.00,
                "currency": "USD",
                "description": "Per report",
                "features": [
                    "Professional PDF report",
                    "Blockchain verified",
                    "Comparable cases analysis",
                    "7-day download access"
                ]
            },
            "premium_subscription": {
                "price": 199.00,
                "currency": "USD",
                "billing_period": "monthly",
                "description": "Unlimited reports",
                "features": [
                    "Unlimited queries",
                    "Unlimited reports",
                    "API access",
                    "Priority support",
                    "Custom integrations"
                ]
            },
            "enterprise": {
                "price": "Custom",
                "currency": "USD",
                "description": "Contact sales",
                "features": [
                    "Everything in Premium",
                    "White-label option",
                    "Dedicated support",
                    "Custom data sources",
                    "SLA guarantee"
                ]
            }
        }


# Global Stripe service instance
stripe_service = StripeService()


