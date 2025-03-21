import os
import stripe
from datetime import datetime, timedelta
from flask import request, redirect, url_for, render_template, jsonify
from flask_login import current_user, login_required

from models import db, User, Subscription, ChatMessage

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

# Set the domain for redirects
domain_url = os.environ.get('REPLIT_DOMAINS', '').split(',')[0]
if domain_url:
    domain_url = f"https://{domain_url}"

def init_app(app):
    """Initialize payment routes and services for the Flask app."""
    
    @app.route('/create-checkout-session', methods=['POST'])
    @login_required
    def create_checkout_session():
        """Create a Stripe checkout session for the enterprise plan."""
        try:
            # Create a new checkout session for the enterprise plan
            checkout_session = stripe.checkout.Session.create(
                customer_email=current_user.email,
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'SpeakDB Enterprise Plan',
                            'description': 'Unlimited database queries, advanced features, and priority support'
                        },
                        'unit_amount': 4900,  # $49.00
                        'recurring': {
                            'interval': 'month'
                        }
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{domain_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{domain_url}/payment/cancel",
                metadata={
                    'user_id': current_user.id
                }
            )
            
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            app.logger.error(f"Error creating checkout session: {str(e)}")
            return render_template('error.html', error=str(e))
    
    @app.route('/payment/success')
    def payment_success():
        """Handle successful payment."""
        session_id = request.args.get('session_id')
        
        if session_id:
            try:
                # Retrieve the session to get customer details
                session = stripe.checkout.Session.retrieve(session_id)
                
                # Get the subscription details
                subscription = stripe.Subscription.retrieve(session.subscription)
                
                # Update user's subscription
                if current_user.is_authenticated:
                    user_subscription = current_user.subscription
                    
                    if not user_subscription:
                        user_subscription = Subscription(user_id=current_user.id)
                        db.session.add(user_subscription)
                    
                    user_subscription.stripe_customer_id = session.customer
                    user_subscription.stripe_subscription_id = session.subscription
                    user_subscription.plan_type = 'enterprise'
                    user_subscription.status = subscription.status
                    
                    # Set subscription end date based on the current period end
                    end_timestamp = subscription.current_period_end
                    user_subscription.end_date = datetime.fromtimestamp(end_timestamp)
                    
                    db.session.commit()
            except Exception as e:
                app.logger.error(f"Error processing successful payment: {str(e)}")
                
        return render_template('payment_success.html')
    
    @app.route('/payment/cancel')
    def payment_cancel():
        """Handle cancelled payment."""
        return render_template('payment_cancel.html')
    
    @app.route('/webhook', methods=['POST'])
    def webhook():
        """Handle Stripe webhook events."""
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get('Stripe-Signature')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            # Invalid payload
            app.logger.error(f"Invalid payload: {str(e)}")
            return jsonify(success=False), 400
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            app.logger.error(f"Invalid signature: {str(e)}")
            return jsonify(success=False), 400
        
        # Handle the event
        if event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            handle_subscription_updated(subscription)
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            handle_subscription_deleted(subscription)
        
        return jsonify(success=True)

def handle_subscription_updated(subscription):
    """Handle subscription updated event."""
    # Find the subscription in our database
    user_subscription = Subscription.query.filter_by(
        stripe_subscription_id=subscription.id
    ).first()
    
    if user_subscription:
        # Update the subscription status and end date
        user_subscription.status = subscription.status
        end_timestamp = subscription.current_period_end
        user_subscription.end_date = datetime.fromtimestamp(end_timestamp)
        db.session.commit()

def handle_subscription_deleted(subscription):
    """Handle subscription deleted event."""
    # Find the subscription in our database
    user_subscription = Subscription.query.filter_by(
        stripe_subscription_id=subscription.id
    ).first()
    
    if user_subscription:
        # Update the subscription type to free and status to inactive
        user_subscription.plan_type = 'free'
        user_subscription.status = 'inactive'
        db.session.commit()

def cancel_subscription(subscription_id):
    """Cancel a Stripe subscription."""
    try:
        stripe.Subscription.delete(subscription_id)
        return True, "Subscription cancelled successfully."
    except Exception as e:
        return False, str(e)

def get_remaining_queries(user):
    """Get remaining queries for a user."""
    # If user has an active enterprise subscription, return unlimited
    if user.subscription and user.subscription.plan_type == 'enterprise' and user.subscription.is_active():
        return 'unlimited'
    
    # Otherwise, calculate remaining queries for free users
    return user.get_remaining_free_queries()