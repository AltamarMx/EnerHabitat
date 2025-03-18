import configparser


def get_list_materials(file):
    config = configparser.ConfigParser()
    config.read(file)
    materials = config.sections()
    return materials

def read_materials(archivo):
    propiedades = configparser.ConfigParser()
    propiedades.read(archivo)

    class Material:
        def __init__(self, k, rho, c):
            self.k = k
            self.rho = rho
            self.c = c

    materiales = {}
    for seccion in propiedades.sections():
        k = float(propiedades[seccion]['k'])
        rho = float(propiedades[seccion]['rho'])
        c = float(propiedades[seccion]['c'])
        materiales[seccion] = Material(k, rho, c)
    
    return materiales

import configparser

def read_configuration(file):
    values = configparser.ConfigParser()
    values.read(file)

    class Configuration:
        def __init__(self, La, Nx,ho,hi,dt):
            # self.dt = dt
            self.La = La
            self.Nx = Nx
            self.ho = ho
            self.hi = hi
            self.dt = dt

    section = 'configuration'
    # dt = float(values[section]['dt'])
    La = float(values[section]['La'])
    Nx = int(values[section]['Nx'])
    ho = float(values[section]['ho'])
    hi = float(values[section]['hi'])
    dt = int(values[section]['dt'])

    configuration = Configuration( La, Nx,ho,hi,dt)
    
    return configuration

