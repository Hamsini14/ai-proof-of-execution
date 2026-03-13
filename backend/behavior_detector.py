from typing import List, Dict, Any

def analyze_behavior(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes execution records for suspicious AI patterns.
    Rule 1: 5 consecutive rejections in recent history.
    Rule 2: >80% rejection rate in last 10 records.
    """
    # Sort by timestamp descending
    sorted_records = sorted(records, key=lambda x: x.get('timestamp', ''), reverse=True)
    recent_10 = sorted_records[:10]
    
    if not recent_10:
        return {
            "is_suspicious": False,
            "reason": None,
            "rejection_rate": 0.0,
            "consecutive_rejections": 0
        }

    # Count consecutive rejections
    consecutive_rejections = 0
    for rec in sorted_records:
        if rec.get('decision') == 'Loan Rejected':
            consecutive_rejections += 1
        else:
            break
            
    # Calculate rejection rate for recent 10
    total_recent = len(recent_10)
    rejection_count = sum(1 for rec in recent_10 if rec.get('decision') == 'Loan Rejected')
    rejection_rate = (rejection_count / total_recent) * 100 if total_recent > 0 else 0.0
    
    # Determine suspicious status
    is_suspicious = False
    reasons = []
    
    if consecutive_rejections >= 5:
        is_suspicious = True
        reasons.append(f"Detected {consecutive_rejections} consecutive rejections")
        
    if recent_10 and rejection_rate >= 80:
        is_suspicious = True
        reasons.append(f"Anomalous rejection rate: {rejection_rate:.1f}%")
        
    return {
        "is_suspicious": is_suspicious,
        "reason": " & ".join(reasons) if reasons else None,
        "rejection_rate": round(rejection_rate, 1),
        "consecutive_rejections": consecutive_rejections
    }
