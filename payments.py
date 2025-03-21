import os
import stripe
from flask import redirect, url_for, request, jsonify, render_template
from flask_login import current_user, login_required
from models import db, Subscription
from datetime import datetime, timedelta

# Set Stripe API key
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Enterprise plan price ID (to be created in Stripe Dashboard)
ENTERPRISE_PLAN_PRICE_ID = "price_enterprise"

def init_app(app):
    """Initialize payment routes and services for the Flask app."""
    
    @app.route('/create-checkout-session', methods=['POST'])
    @login_required
    def create_checkout_session():
        """Create a Stripe checkout session for the enterprise plan."""
        try:
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            # Create or get customer
            customer = None
            if current_user.subscription and current_user.subscription.stripe_customer_id:
                customer = current_user.subscription.stripe_customer_id
            else:
                # Create a customer in Stripe
                stripe_customer = stripe.Customer.create(
                    email=current_user.email,
                    name=current_user.name,
                    metadata={
                        'user_id': current_user.id
                    }
                )
                customer = stripe_customer.id
                
                # Update user's subscription record if it exists
                if current_user.subscription:
                    current_user.subscription.stripe_customer_id = customer
                    db.session.commit()
            
            # Create a checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=customer,
                payment_method_types=['card'],
                line_items=[{
                    'price': ENTERPRISE_PLAN_PRICE_ID,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{request.host_url}payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{request.host_url}payment/cancel",
                metadata={
                    'user_id': current_user.id,
                }
            )
            
            return redirect(checkout_session.url, code=303)
            
        except Exception as e:
            return str(e), 400
    
    @app.route('/payment/success')
    @login_required
    def payment_success():
        """Handle successful payment."""
        session_id = request.args.get('session_id')
        if not session_id:
            return redirect(url_for('pricing'))
        
        try:
            # Retrieve the checkout session
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            
            # Get the subscription ID
            subscription_id = checkout_session.subscription
            
            # Update the user's subscription in the database
            if current_user.subscription:
                current_user.subscription.stripe_subscription_id = subscription_id
                current_user.subscription.plan_type = 'enterprise'
                current_user.subscription.status = 'active'
                current_user.subscription.end_date = datetime.utcnow() + timedelta(days=365)  # Set to 1 year by default
            else:
                # Create a new subscription record
                subscription = Subscription(
                    user_id=current_user.id,
                    stripe_customer_id=checkout_session.customer,
                    stripe_subscription_id=subscription_id,
                    plan_type='enterprise',
                    status='active',
                    end_date=datetime.utcnow() + timedelta(days=365)
                )
                db.session.add(subscription)
            
            db.session.commit()
            
            return render_template('payment_success.html')
            
        except Exception as e:
            return str(e), 400
    
    @app.route('/payment/cancel')
    @login_required
    def payment_cancel():
        """Handle cancelled payment."""
        return render_template('payment_cancel.html')
    
    @app.route('/webhook', methods=['POST'])
    def webhook():
        """Handle Stripe webhook events."""
        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')
        
        # This is your webhook endpoint secret from the Stripe dashboard
        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        
        try:
            if webhook_secret:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            else:
                # For testing, you can parse the payload directly
                payload_json = request.json
                event = stripe.Event.construct_from(payload_json, stripe.api_key)
            
            # Handle the event
            if event['type'] == 'invoice.paid':
                # Handle successful payment
                invoice = event['data']['object']
                subscription_id = invoice.get('subscription')
                
                # Update subscription status if found
                if subscription_id:
                    subscription = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
                    if subscription:
                        subscription.status = 'active'
                        db.session.commit()
                
            elif event['type'] == 'invoice.payment_failed':
                # Handle failed payment
                invoice = event['data']['object']
                subscription_id = invoice.get('subscription')
                
                # Update subscription status if found
                if subscription_id:
                    subscription = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
                    if subscription:
                        subscription.status = 'past_due'
                        db.session.commit()
                
            elif event['type'] == 'customer.subscription.deleted':
                # Handle subscription cancellation
                subscription_object = event['data']['object']
                subscription_id = subscription_object.get('id')
                
                # Update subscription status if found
                if subscription_id:
                    subscription = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
                    if subscription:
                        subscription.status = 'canceled'
                        db.session.commit()
            
            return jsonify(success=True)
            
        except Exception as e:
            return jsonify(success=False, error=str(e)), 400

def cancel_subscription(subscription_id):
    """Cancel a Stripe subscription."""
    try:
        # Cancel the subscription in Stripe
        stripe.Subscription.delete(subscription_id)
        
        # Update the subscription in the database
        subscription = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
        if subscription:
            subscription.status = 'canceled'
            db.session.commit()
        
        return True, None
    except Exception as e:
        return False, str(e)

def get_remaining_queries(user):
    """Get remaining queries for a user."""
    if user.subscription and user.subscription.is_active() and user.subscription.plan_type == 'enterprise':
        return float('inf')  # Enterprise users get unlimited queries
    else:
        return user.get_remaining_free_queries()  # Free users get 10 queries per day