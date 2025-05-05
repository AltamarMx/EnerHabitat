import pvlib
import pytz

from datetime import datetime
from .ehtools import *

def calculateTsa(epw_file_path: str,
    solar_absortance: float,
    surface_tilt: float,
    surface_azimuth: float,
    convection_heat_transfer: float = 13,
    day: str = "15",
    month: str = "current_month",
    year: str = "current_year",
) -> pd.DataFrame:
    """
       Calculates the sun-air temperature per second for the average day experienced by a surface based on EPW file data.

    Args:
        epw_file_path (str): Path to the EPW file.
        solar_absortance (float): Solar absorptance of the system's external material.
        surface_tilt (float): Surface tilt relative to the ground (90° == Vertical).
        surface_azimuth (float): Deviation from true north (0° == North).
        convection_heat_transfer (float): Convective heat transfer coefficient of the system (e.g., 13).
        day (str, optional): Day of interest. Defaults to "15".
        month (str, optional): Month of interest. Defaults to "current_month".
        year (str, optional): Year of interest. Defaults to "current_year".

    Returns:
        pd.DataFrame: Predicted sun-air temperature (TSA) per second for the average day of the specified month and year.
    """
    
    if month == "current_month": month = datetime.now().month
    if year == "current_year": year = datetime.now().year

    # Parámetros de la superficie
    # tilt = 90 = Vertical
    # azimuth = 270

    if surface_tilt == 0:
        LWR = 3.9
    else:
        LWR = 0.

    f1 = f'{year}-{month}-{day} 00:00'
    f2 = f'{year}-{month}-{day} 23:59'
    
    epw, latitud, longitud, altitud, timezone = readEPW(epw_file_path,year,alias=True,warns=False)
    timezone=pytz.timezone('Etc/GMT'+f'{(-timezone):+}')
    
    dia = pd.date_range(start=f1, end=f2, freq='1s',tz=timezone)
    location = pvlib.location.Location(latitude = latitud, 
                                       longitude=longitud, 
                                       altitude=altitud,
                                       tz=timezone)

    dia = location.get_solarposition(dia)
    del dia['apparent_zenith']
    del dia['apparent_elevation']
    
    sunrise,_ = get_sunrise_sunset_times(dia)
    tTmax,Tmin,Tmax = calculate_tTmaxTminTmax(month,epw)

    # Calcular la temperatura ambiente y agregarla al DataFrame
    dia = temperature_model(dia, Tmin, Tmax, sunrise, tTmax)
    
    # Agrega Ig, Ib, Id a dia 
    dia = add_IgIbId_Tn(dia,epw,month,f1,f2,timezone)
    
    total_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt=surface_tilt,
        surface_azimuth=surface_azimuth,
        dni=dia['Ib'],
        ghi=dia['Ig'],
        dhi=dia['Id'],
        solar_zenith=dia['zenith'],
        solar_azimuth=dia['azimuth']
    )
    dia['Is'] = total_irradiance.poa_global
    
    # Agrega Tsa, DeltaTn
    dia['Tsa'] = dia.Ta + dia.Is*solar_absortance/convection_heat_transfer - LWR
    DeltaTa= dia.Ta.max() - dia.Ta.min()

    dia['DeltaTn'] = calculate_DtaTn(DeltaTa)
    
    epw_mes = epw.loc[epw.index.month==int(month)]
    hora_minutos = epw_mes.resample('D').To.idxmax()
    hora = hora_minutos.dt.hour
    minuto = hora_minutos.dt.minute
    tTmax = hora.mean() +  minuto.mean()/60 
    Tmin =  epw_mes.resample('D').To.min().resample('ME').mean().iloc[0]
    Tmax =  epw_mes.resample('D').To.max().resample('ME').mean().iloc[0]

    return dia
    