"""
PHI Protection - HIPAA-compliant PHI detection and redaction for MedinovAI
Handles detection, redaction, and anonymization of Protected Health Information
"""

import re
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import structlog
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

from utils.config import Settings

logger = structlog.get_logger(__name__)


class PHIProtector:
    """
    HIPAA-compliant PHI protection system.
    Detects and redacts Protected Health Information in conversations.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.analyzer: Optional[AnalyzerEngine] = None
        self.anonymizer: Optional[AnonymizerEngine] = None
        
        # PHI patterns for enhanced detection
        self.phi_patterns = self._initialize_phi_patterns()
        
        # Redaction configuration
        self.redaction_enabled = settings.phi_redaction_enabled
        self.audit_logging = settings.audit_logging_enabled
        
        logger.info("PHI protector initialized")
    
    async def initialize(self) -> None:
        """Initialize PHI protection engines."""
        try:
            if self.redaction_enabled:
                # Initialize Presidio analyzer and anonymizer
                self.analyzer = AnalyzerEngine()
                self.anonymizer = AnonymizerEngine()
                
                logger.info("PHI protection engines initialized")
            else:
                logger.warning("PHI redaction is disabled - not HIPAA compliant")
                
        except Exception as e:
            logger.error("Failed to initialize PHI protection", error=str(e))
            raise
    
    async def detect_and_redact(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Detect PHI in text and return redacted version.
        Returns (phi_detected: bool, redacted_text: str)
        """
        if not self.redaction_enabled:
            return False, text
        
        try:
            # Use Presidio for initial detection
            phi_detected = False
            redacted_text = text
            
            if self.analyzer and self.anonymizer:
                # Analyze text for PII/PHI
                results = self.analyzer.analyze(
                    text=text,
                    entities=[
                        "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", 
                        "SSN", "CREDIT_CARD", "DATE_TIME",
                        "MEDICAL_LICENSE", "US_PASSPORT"
                    ],
                    language="en"
                )
                
                if results:
                    phi_detected = True
                    
                    # Anonymize detected entities
                    anonymized_result = self.anonymizer.anonymize(
                        text=text,
                        analyzer_results=results
                    )
                    redacted_text = anonymized_result.text
            
            # Additional custom PHI detection
            custom_phi_detected, custom_redacted = await self._detect_custom_phi(
                redacted_text
            )
            
            if custom_phi_detected:
                phi_detected = True
                redacted_text = custom_redacted
            
            # Log PHI detection if audit logging is enabled
            if self.audit_logging and phi_detected:
                await self._log_phi_detection(text, context)
            
            return phi_detected, redacted_text
            
        except Exception as e:
            logger.error("PHI detection failed", error=str(e))
            # Return original text if detection fails
            return False, text
    
    async def anonymize_for_analytics(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Anonymize data for analytics while preserving utility."""
        if not self.redaction_enabled:
            return data
        
        anonymized_data = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                _, anonymized_value = await self.detect_and_redact(value)
                anonymized_data[key] = anonymized_value
            elif isinstance(value, dict):
                anonymized_data[key] = await self.anonymize_for_analytics(value)
            elif isinstance(value, list):
                anonymized_data[key] = [
                    await self.anonymize_for_analytics(item) if isinstance(item, dict)
                    else item for item in value
                ]
            else:
                anonymized_data[key] = value
        
        return anonymized_data
    
    def hash_phi(self, phi_value: str) -> str:
        """Create consistent hash for PHI (for tracking without storing)."""
        # Use SHA-256 with salt for consistent hashing
        salt = self.settings.encryption_key.get_secret_value()[:16] if self.settings.encryption_key else "default_salt"
        combined = f"{salt}{phi_value}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _initialize_phi_patterns(self) -> Dict[str, re.Pattern]:
        """Initialize regex patterns for PHI detection."""
        patterns = {}
        
        # Medical Record Numbers (MRN)
        patterns["mrn"] = re.compile(
            r'\b(?:mrn|medical\s+record|patient\s+id)[:\s#]*([a-z0-9\-]{6,})\b',
            re.IGNORECASE
        )
        
        # Insurance ID patterns
        patterns["insurance_id"] = re.compile(
            r'\b(?:insurance|policy|member)\s+(?:id|number)[:\s#]*([a-z0-9\-]{8,})\b',
            re.IGNORECASE
        )
        
        # Date of Birth patterns
        patterns["dob"] = re.compile(
            r'\b(?:dob|date\s+of\s+birth|born)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b',
            re.IGNORECASE
        )
        
        # Prescription numbers
        patterns["prescription"] = re.compile(
            r'\b(?:rx|prescription)[:\s#]*([a-z0-9\-]{6,})\b',
            re.IGNORECASE
        )
        
        # Appointment IDs
        patterns["appointment_id"] = re.compile(
            r'\b(?:appointment|appt)[:\s#]*([a-z0-9\-]{6,})\b',
            re.IGNORECASE
        )
        
        return patterns
    
    async def _detect_custom_phi(self, text: str) -> Tuple[bool, str]:
        """Detect custom PHI patterns not covered by Presidio."""
        phi_detected = False
        redacted_text = text
        
        for pattern_name, pattern in self.phi_patterns.items():
            matches = pattern.findall(text)
            if matches:
                phi_detected = True
                
                # Replace matches with redacted placeholders
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]  # Get first capture group
                    
                    placeholder = f"[REDACTED_{pattern_name.upper()}]"
                    redacted_text = redacted_text.replace(match, placeholder)
        
        # Additional checks for healthcare-specific PHI
        
        # Diagnosis codes (ICD-10)
        icd_pattern = re.compile(r'\b[A-Z]\d{2}(?:\.\d{1,3})?\b')
        if icd_pattern.search(text):
            phi_detected = True
            redacted_text = icd_pattern.sub('[REDACTED_DIAGNOSIS_CODE]', redacted_text)
        
        # Lab values with specific ranges
        lab_pattern = re.compile(
            r'\b(?:glucose|cholesterol|blood\s+pressure)\s*:?\s*\d+(?:\.\d+)?(?:\s*mg/dl|mmhg)?\b',
            re.IGNORECASE
        )
        if lab_pattern.search(text):
            phi_detected = True
            redacted_text = lab_pattern.sub('[REDACTED_LAB_VALUE]', redacted_text)
        
        return phi_detected, redacted_text
    
    async def _log_phi_detection(
        self,
        original_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log PHI detection for audit purposes."""
        try:
            audit_entry = {
                "event": "phi_detected",
                "timestamp": datetime.utcnow().isoformat(),
                "text_length": len(original_text),
                "text_hash": hashlib.sha256(original_text.encode()).hexdigest(),
                "context": context or {},
                "detection_method": "automated"
            }
            
            # In production, this would go to a secure audit log
            logger.warning(
                "PHI detected and redacted",
                audit_entry=audit_entry,
                extra={"audit": True}
            )
            
        except Exception as e:
            logger.error("Failed to log PHI detection", error=str(e))
    
    def get_phi_statistics(self) -> Dict[str, Any]:
        """Get PHI detection statistics."""
        # In production, this would return actual statistics
        return {
            "total_messages_processed": 0,
            "phi_detections": 0,
            "detection_rate": 0.0,
            "last_detection": None
        } 