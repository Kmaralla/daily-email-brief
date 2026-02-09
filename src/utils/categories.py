"""Shared category logic for email classification."""


def categorize_sender(sender: str, subject: str) -> str:
    """Categorize sender based on email content and sender name."""
    sender_lower = (sender or '').lower()
    subject_lower = (subject or '').lower()

    if any(w in sender_lower for w in ['newsletter', 'digest', 'news', 'update', 'substack', 'medium']):
        return 'Newsletters'
    if any(w in sender_lower or w in subject_lower for w in ['promo', 'sale', 'deal', 'offer', 'discount', 'coupon', '$', 'fare', 'airline', 'hotel', 'booking']):
        return 'Promotions'
    if any(w in sender_lower for w in ['hospital', 'clinic', 'medical', 'health', 'doctor', 'pharmacy', 'appointment']):
        return 'Healthcare'
    if any(w in sender_lower for w in ['bank', 'credit', 'payment', 'invoice', 'billing', 'paypal', 'stripe', 'financial']):
        return 'Financial'
    if any(w in sender_lower for w in ['linkedin', 'twitter', 'facebook', 'instagram', 'social']):
        return 'Social Media'
    if any(w in sender_lower for w in ['job', 'career', 'recruiter', 'hiring', 'interview', 'application']):
        return 'Work/Jobs'
    if any(w in subject_lower for w in ['security', 'alert', 'login', 'password', 'verify', 'suspicious']):
        return 'Security Alerts'
    if any(w in sender_lower for w in ['amazon', 'ebay', 'shop', 'store', 'retail', 'delivery', 'shipping']):
        return 'Shopping'
    if any(w in sender_lower for w in ['github', 'stackoverflow', 'tech', 'software', 'developer', 'code']):
        return 'Technology'
    if any(w in sender_lower for w in ['university', 'school', 'course', 'education', 'learning', 'coursera', 'udemy']):
        return 'Education'
    if any(w in sender_lower for w in ['travel', 'trip', 'flight', 'airline', 'hotel', 'booking', 'expedia']):
        return 'Travel'
    if any(w in sender_lower for w in ['noreply', 'no-reply', 'notification', 'alert', 'reminder']):
        return 'Notifications'

    return 'Other'
