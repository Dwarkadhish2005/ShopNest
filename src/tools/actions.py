import uuid

def check_order_status(order_id: str) -> str:
    """
    Check the current status of an order.
    Args:
        order_id (str): The ID of the order to check.
    Returns:
        str: The status of the order (e.g., 'shipped', 'delivered', 'pending').
    """
    if not order_id:
        return "Please provide an order ID to check its status."

    # Mock business logic
    if "123" in order_id:
        return f"Order {order_id} is currently: pending"
    elif "456" in order_id:
        return f"Order {order_id} is currently: shipped"
    else:
        return f"Order {order_id} is currently: delivered"


def cancel_order(order_id: str) -> str:
    """
    Cancel an existing order.
    
    Args:
        order_id (str): The ID of the order to cancel.
        
    Returns:
        str: Confirmation message of the cancellation.
    """
    if not order_id:
        return "Please provide an order ID to cancel."
        
    # Mock business logic
    return f"Order {order_id} has been successfully canceled."


def initiate_refund(order_id: str) -> str:
    """
    Initiate a refund for a given order.
    
    Args:
        order_id (str): The ID of the order to refund.
        
    Returns:
        str: Confirmation message of the refund initiation.
    """
    if not order_id:
        return "Please provide an order ID to initiate a refund."
        
    # Mock business logic
    return f"Refund for order {order_id} has been initiated. It should be processed within 3-5 business days."


def create_support_ticket(issue: str) -> str:
    """
    Create a support ticket for a customer issue.
    
    Args:
        issue (str): The description of the issue or problem.
        
    Returns:
        str: Confirmation message with a ticket ID.
    """
    if not issue:
        return "Please provide a description of the issue."
        
    # Mock business logic – generate a unique ticket ID
    ticket_id = "TKT-" + uuid.uuid4().hex[:6].upper()
    return f"Support ticket {ticket_id} has been created for your issue: '{issue}'. Our team will reach out soon."
