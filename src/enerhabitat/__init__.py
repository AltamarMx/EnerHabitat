import pvlib
import locale
import pytz

from .ehtools import *

def calculateTSA(file, ho, solar_absortance, inclination, azimuth, month):
    """
    Calculate TSA for a surface based on EPW file 

    Arguments:
    ----------
    file -- path location of EPW file
    ho -- 13.
    solar_absortance -- Solar absortance for the material
    inclination -- Inclination of the surface 90 - Vertical
    azimuth -- 270
    month -- Month of interest "01, 02, ...11, 12"
    """
    
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    timezone = pytz.timezone('America/Mexico_City')
    
    epw = readEPW(file,alias=True,year='2024',warns=False)
    
    lat = 18.8502768
    lon = -99.2837051
    altitude = 1280
    
    dia = '15'
    mes = month
    absortancia = solar_absortance
    h = ho

    # Parámetros de la superficie
    surface_tilt = inclination  # 90 - Vertical
    surface_azimuth = azimuth  # 270

    if surface_tilt == 0:
        LWR = 3.9
    else:
        LWR = 0.

    f1 = f'2024-{mes}-{dia} 00:00'
    f2 = f'2024-{mes}-{dia} 23:59'

    dia = pd.date_range(start=f1, end=f2, freq='1s',tz=timezone)
    location = pvlib.location.Location(latitude = lat, 
                                       longitude=lon, 
                                       altitude=altitude,
                                       tz=timezone,
                                       name='Temixco,Mor')

    dia = location.get_solarposition(dia)
    del dia['apparent_zenith']
    del dia['apparent_elevation']
    
    sunrise,_ = get_sunrise_sunset_times(dia)
    tTmax,Tmin,Tmax = calculate_tTmaxTminTmax(mes,epw)

    # Calcular la temperatura ambiente y agregarla al DataFrame
    dia = temperature_model(dia, Tmin, Tmax, sunrise, tTmax)
    
    # Agrega Ig, Ib, Id a dia 
    dia = add_IgIbId_Tn(dia,epw,mes,f1,f2,timezone)
    
    # Agrega Tsa, DeltaTn
    dia['Tsa'] = dia.Ta + dia.Is*absortancia/h - LWR
    DeltaTa= dia.Ta.max() - dia.Ta.min()

    dia['DeltaTn'] = calculate_DtaTn(DeltaTa)
    
    epw_mes = epw.loc[epw.index.month==int(mes)]
    hora_minutos = epw_mes.resample('D').To.idxmax()
    hora = hora_minutos.dt.hour
    minuto = hora_minutos.dt.minute
    tTmax = hora.mean() +  minuto.mean()/60 
    Tmin =  epw_mes.resample('D').To.min().resample('ME').mean().iloc[0]
    Tmax =  epw_mes.resample('D').To.max().resample('ME').mean().iloc[0]

"""
def plot_Tsa_Ta(dia):
    
    df = dia.reset_index().iloc[::600]
    fig = px.line(df,x="index",y=["Tsa","Ta"])
    fig.add_trace(go.Scatter(
                            x=df["index"], 
                            y=df['Tn'] + df['DeltaTn'], 
                            mode='lines',
                            showlegend=False , 
                            line=dict(color='rgba(0,0,0,0)')
                            )
    )
    
    fig.add_trace(go.Scatter(
                            x=df["index"], 
                            y=df['Tn'] -df['DeltaTn'], 
                            mode='lines',
                            showlegend=False , 
                            fill='tonexty',
                            line=dict(color='rgba(0,0,0,0)'),
                            fillcolor='rgba(0,255,0,0.3)'
                            )
    )
    
    # Personalizar el layout
    
    fig.update_layout(
        yaxis_title='Temperatura (°C)',
        legend_title='',  # Quitar el título de la leyenda
        xaxis_title=''
    )
    return fig

def plot_I(dia):
    df = dia.reset_index().iloc[::600]
    fig = px.line(df,x="index",y=["Ig","Ib","Id","Is"])

# Personalizar el layout
    fig.update_layout(
        yaxis_title='Temp (oC)',
        legend_title='',  # Quitar el título de la leyenda
        xaxis_title=''
    )
    return fig 
"""