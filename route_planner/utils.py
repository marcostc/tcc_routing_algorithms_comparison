# route_planner/utils.py

import time
import tkinter as tk

def timed(func):
    """
    Decorador para medir o tempo de execução de uma função.
    
    Args:
        func (function): Função a ser decorada.
    Returns:
        function: Função decorada.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        func_name = func.__name__.replace('_', ' ').capitalize()
        print(f"Tempo de execução de {func_name}: {end_time - start_time:.6f} segundos")
        return result
    return wrapper

class RedirectText(object):
    """
    Classe para redirecionar stdout e stderr para um widget Text do Tkinter.
    Attributes:
        text_widget (tk.Text): O widget de texto do Tkinter em que a saída será exibida.
    """
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        """
        Agendar a atualização do widget no thread principal
        Args:
            string (str): A string a ser escrita.
        """ 
        self.text_widget.after(0, self._append_text, string)

    def _append_text(self, string):
        """
        Acrescenta texto ao widget Text.
        Args:
            string (str): A cadeia de caracteres a ser anexada.
        """
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)  # Rolar para o final

    def flush(self):
        """Método de descarga necessário para objetos do tipo arquivo."""
        pass
