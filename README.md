# PythonLeankitMetrics

## Usage
This script gathers metrics from a LeanKit board and creates visual representations of data using Plotly.  

You will need a [LeanKit](https://leankit.com/) account with an active board, and an account at [Plotly](https://plot.ly/)
to push the metrics to.

## Dependencies  
python 3.6  
```bash
pip install leankit  
pip install pytz  
pip install plotly   
pip install python-dateutil
```
## Run from command line 
```bash
python metrics.py [leankit_domain][leankit_username][leankit_password][plotly_username][plotly_api_key]
```

## Note:
You will need to update lane names, etc. as values change on the board.

## Recommendation
Create a job in crontab to run [every hour](https://crontab.guru/every-1-hour) to update metrics.

```bash
sudo crontab -e
```
