import logging
import config

logger = logging.getLogger(__name__)

def is_allowed_email(sender: str, subject: str) -> bool:
    """
    Checks if the email is allowed based on allowed domains and subject keywords.
    """
    # 1. Domain Check
    if config.ALLOWED_DOMAINS:
        domain_match = any(d in sender for d in config.ALLOWED_DOMAINS)
        if not domain_match:
            logger.info(f"Filtered out by sender domain: {sender}")
            return False

    # 2. Subject Keyword Check
    if config.SUBJECT_KEYWORDS:
        keyword_match = any(k in subject for k in config.SUBJECT_KEYWORDS)
        if not keyword_match:
            logger.info(f"Filtered out by subject keyword: {subject}")
            return False
            
    return True
