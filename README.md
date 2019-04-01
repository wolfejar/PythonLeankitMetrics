# PythonLeankitMetrics

## Usage
This script gathers metrics from leankit board and create visual representations of data using plotly.  

You will need a [Leankit](https://leankit.com/) account with an active board, and an account at [Plotly](https://plot.ly/)
to push the metrics to.

## Recomendation
Create a job in crontab to run [every hour](https://crontab.guru/every-1-hour) to update metrics.

```bash
sudo crontab -e
```

## Dependencies:  
python 3.6  
```bash
pip install leankit  
pip install pytz  
pip install plotly   
pip install python-dateutil
```
## Run from command line: 
```bash
python metrics.py [leankit_domain][leankit_username][leankit_password][plotly_username][plotly_api_key]
```
