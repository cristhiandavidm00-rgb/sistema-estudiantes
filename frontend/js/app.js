const API = 'http://localhost:5000/api';
const $ = (id) => document.getElementById(id);

const estado = { token: null, usuario: null, page: 1, per_page: 5, search: '', orden: 'id', direccion: 'asc', totalPages: 1 };

// ───────────── Utilidades ─────────────
function esc(v) {
    const d = document.createElement('div');
    d.textContent = v ?? '';
    return d.innerHTML;
}

function toast(msg, tipo = 'ok') {
    const t = document.createElement('div');
    t.className = `toast ${tipo}`;
    t.textContent = msg;
    $('toast-container').appendChild(t);
    setTimeout(() => t.remove(), 3500);
}

function guardarSesion() {
    localStorage.setItem('token', estado.token);
    localStorage.setItem('usuario', JSON.stringify(estado.usuario));
}
function limpiarSesion() {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    estado.token = null; estado.usuario = null;
}

// fetch con JWT; si el token expira/revoca (401) cierra la sesión
async function api(ruta, opciones = {}) {
    const headers = { 'Content-Type': 'application/json', ...(opciones.headers || {}) };
    if (estado.token) headers['Authorization'] = `Bearer ${estado.token}`;
    const resp = await fetch(`${API}${ruta}`, { ...opciones, headers });
    let data = {};
    try { data = await resp.json(); } catch (_) { /* sin cuerpo */ }
    if (resp.status === 401 && estado.token) {
        limpiarSesion();
        mostrarAuth();
        toast(data.error || 'Sesión expirada', 'error');
    }
    return { ok: resp.ok, status: resp.status, data };
}

// ───────────── Validación en tiempo real ─────────────
const RE_NOMBRE = /^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$/;
const RE_EMAIL = /^[\w.+-]+@[\w-]+(\.[\w-]+)+$/;
const RE_TEL = /^\+?[0-9\s-]{7,20}$/;
const RE_USER = /^[a-zA-Z0-9_]{3,50}$/;

const reglas = {
    nombre: (v) => !v.trim() ? 'El nombre es obligatorio' : v.trim().length < 2 ? 'Mínimo 2 caracteres' : !RE_NOMBRE.test(v.trim()) ? 'Solo puede contener letras' : '',
    apellido: (v) => !v.trim() ? 'El apellido es obligatorio' : v.trim().length < 2 ? 'Mínimo 2 caracteres' : !RE_NOMBRE.test(v.trim()) ? 'Solo puede contener letras' : '',
    edad: (v) => v === '' ? 'La edad es obligatoria' : (!Number.isInteger(Number(v)) || Number(v) < 15 || Number(v) > 100) ? 'La edad debe estar entre 15 y 100' : '',
    carrera: (v) => !v.trim() ? 'La carrera es obligatoria' : v.trim().length < 3 ? 'Mínimo 3 caracteres' : '',
    email: (v) => v.trim() && !RE_EMAIL.test(v.trim()) ? 'Email con formato inválido' : '',
    telefono: (v) => v.trim() && !RE_TEL.test(v.trim()) ? 'Teléfono inválido (7-20 dígitos, puede iniciar con +)' : '',
    'login-username': (v) => !v.trim() ? 'El usuario es obligatorio' : '',
    'login-password': (v) => !v ? 'La contraseña es obligatoria' : '',
    'reg-username': (v) => !RE_USER.test(v.trim()) ? 'Usuario de 3-50 caracteres (letras, números o _)' : '',
    'reg-email': (v) => !RE_EMAIL.test(v.trim()) ? 'Email con formato inválido' : '',
    'reg-password': (v) => v.length < 6 ? 'Mínimo 6 caracteres' : '',
};

function mostrarError(id, msg) {
    const el = document.querySelector(`[data-error-for="${id}"]`);
    const input = $(id);
    if (el) el.textContent = msg || '';
    if (input) input.classList.toggle('invalid', !!msg);
}

function validarCampos(ids) {
    let valido = true;
    ids.forEach((id) => {
        const msg = reglas[id]($(id).value);
        mostrarError(id, msg);
        if (msg) valido = false;
    });
    return valido;
}

function activarValidacion(ids) {
    ids.forEach((id) => $(id).addEventListener('input', () => mostrarError(id, reglas[id]($(id).value))));
}

// Muestra errores por campo devueltos por el backend
function errorsBackend(data, mapa = {}) {
    if (data && data.errores) {
        Object.entries(data.errores).forEach(([campo, msg]) => mostrarError(mapa[campo] || campo, msg));
    }
}

const CAMPOS_EST = ['nombre', 'apellido', 'edad', 'carrera', 'email', 'telefono'];
const CAMPOS_LOGIN = ['login-username', 'login-password'];
const CAMPOS_REG = ['reg-username', 'reg-email', 'reg-password'];
activarValidacion(CAMPOS_EST);
activarValidacion(CAMPOS_LOGIN);
activarValidacion(CAMPOS_REG);

// ───────────── Vistas / sesión ─────────────
function mostrarAuth() {
    $('auth-view').style.display = '';
    $('app-view').style.display = 'none';
}

function mostrarApp() {
    $('auth-view').style.display = 'none';
    $('app-view').style.display = '';
    $('user-info').textContent = `${estado.usuario.username} (${estado.usuario.rol})`;
    cargarEstadisticas();
    cargarEstudiantes();
}

$('tab-login').addEventListener('click', () => cambiarTab(true));
$('tab-registro').addEventListener('click', () => cambiarTab(false));
function cambiarTab(login) {
    $('login-form').style.display = login ? '' : 'none';
    $('registro-form').style.display = login ? 'none' : '';
    $('tab-login').classList.toggle('active', login);
    $('tab-registro').classList.toggle('active', !login);
}

$('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validarCampos(CAMPOS_LOGIN)) return;
    try {
        const { ok, data } = await api('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username: $('login-username').value.trim(), password: $('login-password').value }),
        });
        if (!ok) return toast(data.error || 'No se pudo iniciar sesión', 'error');
        estado.token = data.token;
        estado.usuario = data.usuario;
        guardarSesion();
        $('login-form').reset();
        toast(`Bienvenido, ${data.usuario.username}`);
        mostrarApp();
    } catch (err) {
        toast('Error de conexión con el servidor', 'error');
    }
});

$('registro-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validarCampos(CAMPOS_REG)) return;
    try {
        const { ok, data } = await api('/auth/registro', {
            method: 'POST',
            body: JSON.stringify({
                username: $('reg-username').value.trim(),
                email: $('reg-email').value.trim(),
                password: $('reg-password').value,
            }),
        });
        if (!ok) {
            errorsBackend(data, { username: 'reg-username', email: 'reg-email', password: 'reg-password' });
            return toast(data.error || 'No se pudo registrar', 'error');
        }
        toast('Usuario registrado. Ya puedes iniciar sesión');
        $('registro-form').reset();
        cambiarTab(true);
    } catch (err) {
        toast('Error de conexión con el servidor', 'error');
    }
});

$('logout-btn').addEventListener('click', async () => {
    try { await api('/auth/logout', { method: 'POST' }); } catch (_) { /* igual cerramos local */ }
    limpiarSesion();
    mostrarAuth();
    toast('Sesión cerrada');
});

// ───────────── Estadísticas ─────────────
async function cargarEstadisticas() {
    try {
        const { ok, data } = await api('/estudiantes/stats/general');
        if (!ok) return;
        $('stat-total').textContent = data.total_estudiantes;
        $('stat-prom').textContent = data.promedio_edad;
        $('stat-rango').textContent = data.total_estudiantes ? `${data.edad_minima}-${data.edad_maxima}` : '-';
        const top = data.estudiantes_por_carrera[0];
        $('stat-carrera').textContent = top ? `${top.carrera} (${top.cantidad})` : '-';
    } catch (err) { console.error(err); }
}

// ───────────── Listado, búsqueda, orden, paginación ─────────────
async function cargarEstudiantes() {
    const qs = new URLSearchParams({
        page: estado.page, per_page: estado.per_page, search: estado.search,
        orden: estado.orden, direccion: estado.direccion,
    });
    try {
        const { ok, data } = await api(`/estudiantes?${qs}`);
        if (!ok) return toast(data.error || 'Error al cargar estudiantes', 'error');
        const esAdmin = estado.usuario.rol === 'admin';
        const tbody = $('estudiantes-tbody');
        tbody.innerHTML = '';
        if (!data.estudiantes.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="vacio">No se encontraron estudiantes</td></tr>';
        }
        data.estudiantes.forEach((e) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${esc(e.id)}</td><td>${esc(e.nombre)}</td><td>${esc(e.apellido)}</td>
                <td>${esc(e.edad)}</td><td>${esc(e.carrera)}</td><td>${esc(e.email)}</td><td>${esc(e.telefono)}</td>
                <td class="acciones">
                    <button class="btn-editar" data-id="${e.id}">Editar</button>
                    ${esAdmin ? `<button class="btn-eliminar" data-id="${e.id}">Eliminar</button>` : ''}
                </td>`;
            tbody.appendChild(tr);
        });
        const p = data.paginacion;
        estado.totalPages = p.total_pages;
        estado.page = p.page;
        $('pag-info').textContent = `${p.total_items} estudiante(s) en total`;
        $('pag-page').textContent = `Página ${p.page} de ${p.total_pages}`;
        $('prev-btn').disabled = !p.has_prev;
        $('next-btn').disabled = !p.has_next;
    } catch (err) {
        toast('Error de conexión con el servidor', 'error');
    }
}

$('estudiantes-tbody').addEventListener('click', (ev) => {
    const btn = ev.target.closest('button');
    if (!btn) return;
    const id = btn.dataset.id;
    if (btn.classList.contains('btn-editar')) editarEstudiante(id);
    if (btn.classList.contains('btn-eliminar')) eliminarEstudiante(id);
});

$('prev-btn').addEventListener('click', () => { if (estado.page > 1) { estado.page--; cargarEstudiantes(); } });
$('next-btn').addEventListener('click', () => { if (estado.page < estado.totalPages) { estado.page++; cargarEstudiantes(); } });

let debounce;
$('search').addEventListener('input', (e) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => { estado.search = e.target.value.trim(); estado.page = 1; cargarEstudiantes(); }, 400);
});
$('orden').addEventListener('change', (e) => { estado.orden = e.target.value; estado.page = 1; cargarEstudiantes(); });
$('direccion').addEventListener('change', (e) => { estado.direccion = e.target.value; estado.page = 1; cargarEstudiantes(); });
$('per-page').addEventListener('change', (e) => { estado.per_page = Number(e.target.value); estado.page = 1; cargarEstudiantes(); });

// ───────────── CRUD ─────────────
$('estudiante-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validarCampos(CAMPOS_EST)) return;
    const id = $('estudiante-id').value;
    const body = {
        nombre: $('nombre').value.trim(), apellido: $('apellido').value.trim(),
        edad: parseInt($('edad').value, 10), carrera: $('carrera').value.trim(),
        email: $('email').value.trim(), telefono: $('telefono').value.trim(),
    };
    try {
        const { ok, data } = await api(id ? `/estudiantes/${id}` : '/estudiantes', {
            method: id ? 'PUT' : 'POST', body: JSON.stringify(body),
        });
        if (!ok) {
            errorsBackend(data);
            return toast(data.error || 'Error al guardar el estudiante', 'error');
        }
        toast(data.mensaje);
        limpiarFormulario();
        cargarEstudiantes();
        cargarEstadisticas();
    } catch (err) {
        toast('Error de conexión con el servidor', 'error');
    }
});

async function editarEstudiante(id) {
    const { ok, data } = await api(`/estudiantes/${id}`);
    if (!ok) return toast(data.error || 'Error al cargar el estudiante', 'error');
    $('estudiante-id').value = data.id;
    CAMPOS_EST.forEach((c) => { $(c).value = data[c] ?? ''; mostrarError(c, ''); });
    $('form-title').textContent = 'Editar Estudiante';
    $('submit-btn').textContent = 'Actualizar Estudiante';
    $('cancel-btn').style.display = 'block';
    $('estudiante-form').scrollIntoView({ behavior: 'smooth' });
}

async function eliminarEstudiante(id) {
    if (!confirm('¿Estás seguro de eliminar este estudiante?')) return;
    const { ok, data } = await api(`/estudiantes/${id}`, { method: 'DELETE' });
    if (!ok) return toast(data.error || 'Error al eliminar', 'error');
    toast(data.mensaje);
    cargarEstudiantes();
    cargarEstadisticas();
}

function limpiarFormulario() {
    $('estudiante-form').reset();
    $('estudiante-id').value = '';
    CAMPOS_EST.forEach((c) => mostrarError(c, ''));
    $('form-title').textContent = 'Agregar Nuevo Estudiante';
    $('submit-btn').textContent = 'Agregar Estudiante';
    $('cancel-btn').style.display = 'none';
}
$('cancel-btn').addEventListener('click', limpiarFormulario);

// ───────────── Inicio: restaurar sesión desde localStorage ─────────────
(function init() {
    try {
        const token = localStorage.getItem('token');
        const usuario = JSON.parse(localStorage.getItem('usuario') || 'null');
        if (token && usuario) {
            estado.token = token;
            estado.usuario = usuario;
            return mostrarApp();
        }
    } catch (_) { /* sesión corrupta */ }
    mostrarAuth();
})();
