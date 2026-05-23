import uuid

def check_order_status(order_id: str) -> str:
    if not order_id:
        return "Please provide an order ID to check its status."

    
    if "123" in order_id:
        return f"Order {order_id} is currently: pending"
    elif "456" in order_id:
        return f"Order {order_id} is currently: shipped"
    else:
        return f"Order {order_id} is currently: delivered"


def cancel_order(order_id: str) -> str:
    if not order_id:
        return "Please provide an order ID to cancel."
        
    
    return f"Order {order_id} has been successfully canceled."


def initiate_refund(order_id: str) -> str:
    if not order_id:
        return "Please provide an order ID to initiate a refund."
        
    
    return f"Refund for order {order_id} has been initiated. It should be processed within 3-5 business days."


def create_support_ticket(issue: str) -> str:
    if not issue:
        return "Please provide a description of the issue."
        
    
    ticket_id = "TKT-" + uuid.uuid4().hex[:6].upper()
    return f"Support ticket {ticket_id} has been created for your issue: '{issue}'. Our team will reach out soon."
