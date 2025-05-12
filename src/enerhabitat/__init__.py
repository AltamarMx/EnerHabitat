import pvlib
import pytz

from datetime import datetime
from .ehtools import *

def Tsa(
    epw_file,
    solar_absortance: float,
    surface_tilt: float,
    surface_azimuth: float,
    day = "15",
    month = "current_month",
    year = "current_year"
    ) -> pd.DataFrame: 
    """
    Calculates the sun-air temperature per second for the average day experienced by a surface based on EPW file data.
    
    Args:
        epw_file (str): Path to the EPW file. 
        solar_absortance (float): Solar absortance of the system's external material.
        surface_tilt (float): Surface tilt relative to the ground, 90° == Vertical.
        surface_azimuth (float): Deviation from true north, 0° == North.
        day (str, optional): Day of interest. Defaults to "15".
        month (str, optional): Month of interest. Defaults to "current_month".
        year (str, optional): Year of interest. Defaults to "current_year".

    Returns:
        pd.DataFrame: Predicted sun-air temperature (TSA) per second for the average day of the specified month and year.
    """

    eh_config = read_configuration()
    convection_heat_transfer = eh_config.ho
    
    if month == "current_month": month = datetime.now().month
    if year == "current_year": year = datetime.now().year

    if surface_tilt == 0:
        LWR = 3.9
    else:
        LWR = 0.

    f1 = f'{year}-{month}-{day} 00:00'
    f2 = f'{year}-{month}-{day} 23:59'
    
    epw, latitud, longitud, altitud, timezone = readEPW(epw_file,year,alias=True,warns=False)
    timezone=pytz.timezone('Etc/GMT'+f'{(-timezone):+}')
    
    dia_promedio = pd.date_range(start=f1, end=f2, freq='1s',tz=timezone)
    location = pvlib.location.Location(latitude = latitud, 
                                       longitude=longitud, 
                                       altitude=altitud,
                                       tz=timezone)

    dia_promedio = location.get_solarposition(dia_promedio)
    del dia_promedio['apparent_zenith']
    del dia_promedio['apparent_elevation']
    
    sunrise,_ = get_sunrise_sunset_times(dia_promedio)
    tTmax,Tmin,Tmax = calculate_tTmaxTminTmax(month,epw)

    # Calculate ambient temperature y add to the DataFrame
    dia_promedio = temperature_model(dia_promedio, Tmin, Tmax, sunrise, tTmax)
    
    # Add Ig, Ib, Id a dia_promedio 
    dia_promedio = add_IgIbId_Tn(dia_promedio,epw,month,f1,f2,timezone)
    
    total_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt=surface_tilt,
        surface_azimuth=surface_azimuth,
        dni=dia_promedio['Ib'],
        ghi=dia_promedio['Ig'],
        dhi=dia_promedio['Id'],
        solar_zenith=dia_promedio['zenith'],
        solar_azimuth=dia_promedio['azimuth']
    )
    dia_promedio['Is'] = total_irradiance.poa_global
    
    # Add Tsa, DeltaTn
    dia_promedio['Tsa'] = dia_promedio.Ta + dia_promedio.Is*solar_absortance/convection_heat_transfer - LWR
    DeltaTa= dia_promedio.Ta.max() - dia_promedio.Ta.min()

    dia_promedio['DeltaTn'] = calculate_DtaTn(DeltaTa)
    
    epw_mes = epw.loc[epw.index.month==int(month)]
    hora_minutos = epw_mes.resample('D').To.idxmax()
    hora = hora_minutos.dt.hour
    minuto = hora_minutos.dt.minute
    tTmax = hora.mean() +  minuto.mean()/60 
    Tmin =  epw_mes.resample('D').To.min().resample('ME').mean().iloc[0]
    Tmax =  epw_mes.resample('D').To.max().resample('ME').mean().iloc[0]

    return dia_promedio
    
def solveCS(
    constructive_system:list,
    Tsa_dataframe:pd.DataFrame,
    )->pd.DataFrame:
    """
    Solves the constructive system's inside temperature with the TSA simulation dataframe.

    Args:
        constructive_system (list): List of tuples with the material and width
        Tsa_dataframe (pd.DataFrame): Predicted sun-air temperature (TSA) per second for the average day DataFrame.
        
    Returns:
        pd.DataFrame: modified Tsa_dataframe with the constructive system solution.
    """
    
    materiales = get_list_materials()
    propiedades = read_materials()
    eh_config = read_configuration()
    
    cs = set_construction(propiedades, constructive_system)
    Ltotal  = get_total_L(cs)
    
    k, rhoc, dx = set_k_rhoc(cs, eh_config.Nx)

    T = np.full(eh_config.Nx, Tsa_dataframe.Tn.mean())
    Tsa_dataframe['Ti'] = Tsa_dataframe.Tn.mean()
    dt  = eh_config.dt
    nx = eh_config.Nx 
    ho = eh_config.ho
    hi = eh_config.hi
    La = eh_config.La
    
    Tsa_dataframe = Tsa_dataframe.iloc[::dt]
    
    C = 1
    while C > 5e-4: 
        Told = T.copy()
        for tiempo, datos in Tsa_dataframe.iterrows():
            a,b,c,d = calculate_coefficients(dt, dx, k, nx, rhoc, T, datos["Tsa"], ho, datos["Ti"], hi)
            T, Ti = solve_PQ(a, b, c, d, T, nx, datos['Ti'], hi, La, dt)
            Tsa_dataframe.loc[tiempo,"Ti"] = Ti
        Tnew = T.copy()
        C = abs(Told - Tnew).mean()
        FD   = (Tsa_dataframe.Ti.max() - Tsa_dataframe.Ti.min())/(Tsa_dataframe.Ta.max()-Tsa_dataframe.Ta.min())
        FDsa = (Tsa_dataframe.Ti.max() - Tsa_dataframe.Ti.min())/(Tsa_dataframe.Tsa.max()-Tsa_dataframe.Tsa.min())
    
    return Tsa_dataframe