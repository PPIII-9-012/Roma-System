# Roma Automotores — Sistema de Cotización y Créditos Prendarios

Plataforma web para cotización automotriz, valuaciones de mercado vía **InfoAuto** y simulador de créditos prendarios (**PSA Finance** / Líneas Tradicionales y UVA).

---

## 🚀 Requisitos

- Python 3.10 o superior
- Navegador web moderno (Chrome, Edge, Firefox)

---

## 📦 Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/PPIII-9-012/Roma-System.git
   cd Roma-System
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno:**
   Copia el archivo `.env.example` a `.env` y coloca las credenciales oficiales de InfoAuto:
   ```bash
   cp .env.example .env
   ```
   Contenido de `.env`:
   ```env
   INFOAUTO_EMAIL=tu_email@empresa.com
   INFOAUTO_PASSWORD=tu_password
   INFOAUTO_BASE_URL=https://api.infoauto.com.ar
   PORT=5050
   ```

---

## ▶️ Ejecución

Para iniciar el backend y abrir automáticamente la plataforma en el navegador:
```bash
python start.py
```
O directamente con Flask:
```bash
python backend.py
```
La aplicación quedará disponible en: `http://localhost:5050`

---

## 🧪 Pruebas Unitarias

Para ejecutar la suite de pruebas de lógica financiera y aforos:
```bash
python test_logic.py
```

---

## 📂 Estructura del Proyecto

```
Roma-System/
├── backend.py            # API Flask, integración InfoAuto y motor de cálculo prendario
├── index.html            # Interfaz de usuario (Cotizador, Simulador y Resumen)
├── start.py              # Launcher rápido
├── test_logic.py         # Suite de pruebas automatizadas
├── requirements.txt      # Dependencias Python
├── .env.example          # Plantilla de variables de entorno
├── .gitignore            # Exclusiones de Git
├── README.md             # Documentación principal
│
├── *.png / *.jpg         # Assets gráficos e iconografía de la UI
└── archive/              # Documentación técnica previa, borradores y versiones históricas
```

---

## 🛡️ Seguridad

- Las credenciales sensibles (`.env`) están estrictamente excluidas de Git mediante `.gitignore`.
- La autenticación con InfoAuto utiliza tokens JWT de corta duración con refresco automático en memoria.
