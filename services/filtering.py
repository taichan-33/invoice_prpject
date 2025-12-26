import logging
import config

logger = logging.getLogger(__name__)

def is_allowed_email(sender: str, subject: str) -> bool:
    """
    Checks if the email is allowed based on allowed domains and subject keywords.
    Logic is OR: Allowed if (Domain Match) OR (Subject Match).
    """
    # Normalize to lowercase for case-insensitive check
    sender_lower = sender.lower()
    subject_lower = subject.lower()

    has_domain_config = bool(config.ALLOWED_DOMAINS)
    has_subject_config = bool(config.SUBJECT_KEYWORDS)
    
    # If no filtering configured, allow all
    if not has_domain_config and not has_subject_config:
        return True

    # 1. Domain Check (Pass if match)
    if has_domain_config:
        domain_match = any(d.lower() in sender_lower for d in config.ALLOWED_DOMAINS)
        if domain_match:
            logger.info(f"Allowed by sender domain: {sender}")
            return True

    # 2. Subject Keyword Check (Pass if match)
    if has_subject_config:
        keyword_match = any(k.lower() in subject_lower for k in config.SUBJECT_KEYWORDS)
        if keyword_match:
            logger.info(f"Allowed by subject keyword: {subject}")
            return True
            
    # If we reached here, filtering is active but no criteria matched
    logger.info(f"Filtered out (No match for domain or subject): {sender} | {subject}")
    return False
