import numpy as np

def set_construction(propiedades,tuplas):
    """
    Actualiza el diccionario cs con los valores de L y las propiedades del material proporcionados en las tuplas.
    
    Parameters:
    propiedades (dict): Diccionario con las propiedades de los materiales.
    tuplas (list): Lista de tuplas, donde cada tupla contiene el valor de L y el nombre del material.
    
    Returns:
    dict: Diccionario actualizado cs.
    """
    cs ={}
    for i, (L, material) in enumerate(tuplas, start=1):
        capa = f"L{i}"
        cs[capa] = {
            "L": L,
            "material": propiedades[material]
        }
    return cs

def get_total_L(cs):
    L_total = sum([cs[L]["L"] for L in cs.keys()])
    return L_total


def set_k_rhoc(cs, nx):
    """
    Calcula los arreglos de conductividad y el producto de calor específico y densidad
    para cada volumen de control, y también calcula el tamaño de cada volumen de control (dx).
    
    Parameters:
    cs (dict): Diccionario con la configuración del sistema constructivo.
    nx (int): Número de elementos de discretización.
    
    Returns:
    tuple: (k_array, rhoc_array, dx), donde k_array es el arreglo de conductividad,
           rhoc_array es el arreglo del producto de calor específico y densidad,
           y dx es el tamaño de cada volumen de control.
    """
    L_total = get_total_L(cs)
    dx = L_total / nx

    k_array = np.zeros(nx)
    rhoc_array = np.zeros(nx)

    # Inicializar la posición actual en el arreglo
    i = 0

    for L in cs.keys():
        L_value = cs[L]['L']
        k_value = cs[L]['material'].k
        rhoc_value = cs[L]['material'].rho * cs[L]['material'].c

        num_elements = int(L_value / dx)
        
        for j in range(num_elements):
            if i >= nx:
                break
            k_array[i] = k_value
            rhoc_array[i] = rhoc_value
            i += 1

        # Considerar promedio armónico solo con el primer vecino
        if i < nx and i > 0:
            k_array[i] = 2 * (k_array[i-1] * k_value) / (k_array[i-1] + k_value)
            rhoc_array[i] = rhoc_value
            i += 1

    return k_array, rhoc_array, dx



def calculate_coefficients(dt, dx, k, nx, rhoc, T, To, ho, Ti, hi):
    """
    Calcula los coeficientes a, b, c y d para el sistema de ecuaciones.

    Parameters:
    dt (float): Paso temporal.
    dx (float): Tamaño de cada volumen de control.
    k (numpy.ndarray): Arreglo de conductividades.
    nx (int): Número de elementos de discretización.
    rhoc (numpy.ndarray): Arreglo del producto de densidad y calor específico.
    T (numpy.ndarray): Arreglo de temperaturas.
    To (float): Temperatura en el exterior.
    ho (float): Coeficiente convectivo en el exterior.
    Ti (float): Temperatura en el interior.
    hi (float): Coeficiente convectivo en el interior.

    Returns:
    tuple: (a, b, c, d) arreglos de coeficientes.
    """
    a = np.zeros(nx)
    b = np.zeros(nx)
    c = np.zeros(nx)
    d = np.zeros(nx)

    # Calcular coeficientes en el primer nodo
    b[0] = (2.0 * k[0] * k[1]) / (k[0] + k[1]) / dx
    c[0] = 0.0
    d[0] = rhoc[0] * dx / dt * T[0] + ho * To
    a[0] = rhoc[0] * dx / dt + ho + b[0]
    
    # Calcular coeficientes en los nodos intermedios
    for i in range(1, nx -1):
        b[i] = (2.0 * k[i] * k[i + 1]) / (k[i] + k[i + 1]) / dx
        c[i] = (2.0 * k[i - 1] * k[i]) / (k[i] + k[i - 1]) / dx
        d[i] = rhoc[i] * dx / dt * T[i]
        a[i] = rhoc[i] * dx / dt + b[i] + c[i]
    
    # Calcular coeficientes en el último nodo
    i = nx - 1
    b[i] = 0.0
    c[i] = (2.0 * k[i - 1] * k[i]) / (k[i] + k[i - 1]) / dx
    d[i] = rhoc[i] * dx / dt * T[i] + hi * Ti
    a[i] = rhoc[i] * dx / dt + c[i] + hi

    return a, b, c, d

def solve_PQ(a, b, c, d, T, nx, Tint, hi, La, dt):
    """
    Resuelve el sistema de ecuaciones usando el método TDMA y actualiza las temperaturas para el siguiente paso temporal.

    Parameters:
    a (numpy.ndarray): Arreglo de coeficientes a.
    b (numpy.ndarray): Arreglo de coeficientes b.
    c (numpy.ndarray): Arreglo de coeficientes c.
    d (numpy.ndarray): Arreglo de coeficientes d.
    T (numpy.ndarray): Arreglo de temperaturas.
    nx (int): Número de elementos de discretización.
    Tint (float): Temperatura interna.
    hi (float): Coeficiente convectivo interno.
    rhoair (float): Densidad del aire.
    cair (float): Calor específico del aire.
    La (float): Parámetro adicional (longitud, área, etc.).
    dt (float): Paso temporal.
    Qin (float): Calor interno.
    Tintaverage (float): Temperatura interna promedio.
    Ein (float): Energía interna.

    Returns:
    tuple: (T, Tint, Qin, Tintaverage, Ein) arreglos de temperaturas y parámetros actualizados.
    """
    
    rhoair  = 1.1797660470258469
    cair    = 1005.458757
    P = np.zeros(nx)
    Q = np.zeros(nx)
    Tn = np.zeros(nx)
    
    # Inicializar P y Q
    P[0] = b[0] / a[0]
    Q[0] = d[0] / a[0]

    for i in range(1, nx):
        P[i] = b[i] / (a[i] - c[i] * P[i - 1])
        Q[i] = (d[i] + c[i] * Q[i - 1]) / (a[i] - c[i] * P[i - 1])

    Tn[nx - 1] = Q[nx - 1]
    for i in range(nx - 2, -1, -1):
        Tn[i] = P[i] * Tn[i + 1] + Q[i]

    T[:] = Tn

    # Actualizar Tint, Tintaverage, Qin y Ein
    Tinn = Tint
    Tint += hi * dt / (rhoair * cair * La) * (T[nx - 1] - Tinn)

    return T, Tint
