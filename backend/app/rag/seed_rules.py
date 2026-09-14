"""Business rules / SOPs corpus. Retrieved by the agent at decision time via RAG."""

BUSINESS_RULES = [
    "Purchase orders with a total value above 50,000 require buyer approval before execution.",
    "Maintain safety stock covering at least the supplier lead time for each SKU.",
    "For perishable products, do not order more than can realistically be sold within the "
    "product shelf life; prefer smaller, more frequent orders.",
    "If actual sales deviate from the forecast by more than 50%, treat the forecast as "
    "unreliable and investigate before committing to a large purchase.",
    "Prefer the primary supplier; use an alternate supplier only when the primary cannot "
    "fulfill the required quantity within an acceptable lead time.",
    "Never exceed the allocated category budget for a fulfillment node.",
    "Never exceed the available storage capacity at a fulfillment node.",
    "When a supplier confirms less than the ordered quantity, cover the remaining quantity "
    "from an alternate supplier if one is available with acceptable lead time; otherwise "
    "escalate to a human buyer.",
    "Do not place a purchase order below the supplier's minimum order quantity.",
    "If on-hand inventory plus incoming purchase orders already cover expected demand and "
    "safety stock, do not place an additional order.",
]
