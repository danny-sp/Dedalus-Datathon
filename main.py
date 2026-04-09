import os
import subprocess
import sys


def main():
    args = sys.argv[1:]

    if len(args) > 0 and args[0].lower() == "cli":
        print("Iniciando aplicación en modo CLI...")
        from src.presentation.cli_app import run_cli

        run_cli()
    else:
        print("Iniciando aplicación en modo interfaz web (Streamlit)...")
        # Obtenemos la ruta absoluta para asegurarnos de que se ejecute correctamente
        current_dir = os.path.dirname(os.path.abspath(__file__))
        streamlit_app_path = os.path.join(
            current_dir, "src", "presentation", "streamlit_app.py"
        )

        try:
            # Ejecutamos streamlit en un subproceso
            subprocess.run(
                [sys.executable, "-m", "streamlit", "run", streamlit_app_path]
            )
        except KeyboardInterrupt:
            print("\nCerrando aplicación...")


if __name__ == "__main__":
    main()
