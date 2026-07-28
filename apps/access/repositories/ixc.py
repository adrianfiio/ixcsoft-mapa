def load_ixc_customers(client):
    """
    Carrega clientes do IXC em memória.

    Retorna:
    {
        "6": "Nome Cliente",
        "7": "Outro Cliente",
    }
    """

    customers = {}

    for item in client.iter_records(
        "cliente",
        per_page=200,
    ):
        customer_id = item.get("id")

        if not customer_id:
            continue

        name = (
            item.get("razao")
            or item.get("nome_fantasia")
            or ""
        )

        customers[str(customer_id)] = name

    return customers
