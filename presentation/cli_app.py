from domain.agent import get_agent_executor


def run_cli():
    print("Iniciando la base de datos y los modelos de IA...")
    agent_executor = get_agent_executor()

    print("\n" + "=" * 50)
    print("--- Agente Médico Activo (CLI) ---")
    print("Escribe 'salir', 'exit' o 'quit' para terminar el chat.")
    print("=" * 50 + "\n")

    while True:
        try:
            pregunta = input("Tú: ")
            if pregunta.lower().strip() in ["salir", "exit", "quit"]:
                print("Cerrando el asistente...")
                break

            if not pregunta.strip():
                continue

            inputs = {"messages": [("user", pregunta)]}

            for event in agent_executor.stream(inputs, stream_mode="values"):
                message = event["messages"][-1]
                if (
                    hasattr(message, "type")
                    and message.type == "ai"
                    and message.content
                ):
                    print(f"Asistente: {message.content}")
            print()  # Salto de línea por estética

        except KeyboardInterrupt:
            print("\nCerrando el asistente...")
            break
        except Exception as e:
            print(f"\nError inesperado: {e}")


if __name__ == "__main__":
    run_cli()
