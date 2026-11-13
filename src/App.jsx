import React, { useState, useEffect } from 'react';

// Componente principal de la aplicación EDÉN - Asistente Empresarial Inteligente
// Gestiona autenticación, rutas protegidas y navegación interna sin librerías externas.

function App() {
  // Estado para usuario autenticado (objeto con username) o null si no hay sesión
  const [user, setUser] = useState(null);
  // Estado para controlar vistas: 'login', 'register', 'dashboard', 'loading'
  const [view, setView] = useState('loading');
  // Estados para formularios de login y registro
  const [formUsername, setFormUsername] = useState('');
  const [formPassword, setFormPassword] = useState('');
  // Estado para mensajes de error o info
  const [message, setMessage] = useState('');

  // Función para obtener token JWT del localStorage
  const getToken = () => localStorage.getItem('token');

  // Función para guardar token JWT en localStorage
  const saveToken = (token) => localStorage.setItem('token', token);

  // Función para eliminar token y cerrar sesión
  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setView('login');
    setMessage('');
    setFormUsername('');
    setFormPassword('');
  };

  // Función para validar token y obtener datos del usuario (/auth/me)
  const fetchMe = async (token) => {
    try {
      const res = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('No autorizado');
      const data = await res.json();
      setUser({ username: data.username });
      setView('dashboard');
      setMessage('');
    } catch {
      logout();
    }
  };

  // Al montar el componente, intentar validar token guardado para mantener sesión
  useEffect(() => {
    const token = getToken();
    if (token) {
      fetchMe(token);
    } else {
      setView('login');
    }
  }, []);

  // Función para manejar login con formulario
  const handleLogin = async (e) => {
    e.preventDefault();
    setMessage('');
    if (!formUsername || !formPassword) {
      setMessage('Por favor, complete usuario y contraseña.');
      return;
    }
    try {
      const body = new URLSearchParams();
      body.append('username', formUsername);
      body.append('password', formPassword);
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      });
      if (!res.ok) {
        if (res.status === 401) setMessage('Usuario o contraseña incorrectos.');
        else setMessage('Error en el servidor. Intente más tarde.');
        return;
      }
      const data = await res.json();
      saveToken(data.access_token);
      await fetchMe(data.access_token);
      setFormPassword('');
    } catch {
      setMessage('Error de conexión. Verifique su red.');
    }
  };

  // Función para manejar registro con formulario
  const handleRegister = async (e) => {
    e.preventDefault();
    setMessage('');
    if (!formUsername || !formPassword) {
      setMessage('Por favor, complete usuario y contraseña.');
      return;
    }
    try {
      const body = new URLSearchParams();
      body.append('username', formUsername);
      body.append('password', formPassword);
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      });
      if (!res.ok) {
        if (res.status === 400) setMessage('El usuario ya existe o datos inválidos.');
        else setMessage('Error en el servidor. Intente más tarde.');
        return;
      }
      setMessage('Registro exitoso. Ahora puede iniciar sesión.');
      setView('login');
      setFormPassword('');
    } catch {
      setMessage('Error de conexión. Verifique su red.');
    }
  };

  // Renderiza formulario de login
  const renderLogin = () => (
    <main className="auth-container">
      <h1>EDÉN - Iniciar Sesión</h1>
      <form onSubmit={handleLogin} className="auth-form" autoComplete="off">
        <label htmlFor="username">Usuario</label>
        <input
          id="username"
          type="text"
          value={formUsername}
          onChange={(e) => setFormUsername(e.target.value.trim())}
          autoFocus
          required
          autoComplete="username"
        />
        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          type="password"
          value={formPassword}
          onChange={(e) => setFormPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
        <button type="submit" className="btn-primary">Entrar</button>
      </form>
      <p>
        ¿No tiene cuenta?{' '}
        <button className="link-button" onClick={() => { setView('register'); setMessage(''); }}>
          Regístrese aquí
        </button>
      </p>
      {message && <p className="message error">{message}</p>}
    </main>
  );

  // Renderiza formulario de registro
  const renderRegister = () => (
    <main className="auth-container">
      <h1>EDÉN - Registro</h1>
      <form onSubmit={handleRegister} className="auth-form" autoComplete="off">
        <label htmlFor="reg-username">Usuario</label>
        <input
          id="reg-username"
          type="text"
          value={formUsername}
          onChange={(e) => setFormUsername(e.target.value.trim())}
          autoFocus
          required
          autoComplete="username"
        />
        <label htmlFor="reg-password">Contraseña</label>
        <input
          id="reg-password"
          type="password"
          value={formPassword}
          onChange={(e) => setFormPassword(e.target.value)}
          required
          autoComplete="new-password"
        />
        <button type="submit" className="btn-primary">Registrar</button>
      </form>
      <p>
        ¿Ya tiene cuenta?{' '}
        <button className="link-button" onClick={() => { setView('login'); setMessage(''); }}>
          Inicie sesión aquí
        </button>
      </p>
      {message && <p className="message error">{message}</p>}
    </main>
  );

  // Renderiza dashboard protegido (contenido principal de la app)
  const renderDashboard = () => (
    <main className="dashboard-container">
      <header className="dashboard-header">
        <h1>Bienvenido, {user.username}</h1>
        <button className="btn-logout" onClick={logout} title="Cerrar sesión">Salir</button>
      </header>
      <section className="dashboard-content">
        {/* Aquí se pueden agregar componentes hijos para cotizaciones, proyectos, tareas, etc. */}
        <p>Esta es la pantalla principal del asistente empresarial EDÉN.</p>
        <p>Funcionalidades futuras: gestión de cotizaciones, proyectos, costos, tareas y finanzas.</p>
      </section>
    </main>
  );

  // Renderiza pantalla de carga mientras se valida sesión
  const renderLoading = () => (
    <main className="loading-container">
      <p>Cargando...</p>
    </main>
  );

  // Renderizado condicional según vista actual
  return (
    <>
      {view === 'loading' && renderLoading()}
      {view === 'login' && renderLogin()}
      {view === 'register' && renderRegister()}
      {view === 'dashboard' && user && renderDashboard()}
    </>
  );
}

export default App;