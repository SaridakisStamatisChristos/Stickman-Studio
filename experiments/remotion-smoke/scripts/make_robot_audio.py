from pathlib import Path
import subprocess, tempfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, butter, sosfilt
from math import gcd
R=48000; N=12*R;t=np.arange(N)/R; rng=np.random.default_rng(43); mix=np.zeros(N)
def put(a,start,gain=1):
 i=int(start*R); n=min(len(a),N-i)
 if n>0: mix[i:i+n]+=a[:n]*gain
def tone(freq,dur,decay=4):
 x=np.arange(int(dur*R))/R; return (np.sin(2*np.pi*freq*x)+.18*np.sin(2*np.pi*freq*2*x))*np.exp(-decay*x)*np.minimum(x/.012,1)
for i,f in enumerate([110,130.81,164.81,196,220]):
 mix+=.024*np.sin(2*np.pi*f*t+.35*np.sin(t*.5+i))*(.65+.35*np.sin(t*.7+i))*np.minimum(t/.8,1)*np.minimum((12-t)/1.2,1)
for i in range(16):
 st=i*.75; x=np.arange(int(.16*R))/R;put(np.sin(2*np.pi*(75*x-100*x*x))*np.exp(-25*x),st,.10)
for i in range(8):put(tone([440,523.25,659.25,783.99][i%4],.7,5),i*1.5+.2,.035)
for j in range(4):put(tone(500+j*105,.12,25),.5+j*.43,.05)
x=np.arange(int(1.8*R))/R; noise=sosfilt(butter(2,[450,4500],btype='bandpass',fs=R,output='sos'),rng.normal(size=len(x)));put(noise*(x/1.8)**2,3.35,.14)
x=np.arange(int(1.15*R))/R;put((np.sin(2*np.pi*(85*x-20*x*x))+.35*rng.normal(size=len(x)))*np.exp(-7*x),5.1,.22)
for i,f in enumerate([523.25,659.25,783.99,1046.5,1318.51,1567.98]):put(tone(f,1.35,3.5),5.2+i*.095,.09)
for i in range(14):put(tone(700+int(rng.integers(0,1100)),.25,13),5.45+i*.24,.024)
for i,f in enumerate([523.25,659.25,783.99]):put(tone(f,.9,4),9.2+i*.09,.065)
phrases=[(0.22,'A little robot found a chest.'),(2.7,'But inside, something shone.'),(5.42,'Two hundred fifty thousand stars.'),(8.98,'No AI video. Just code.')]
with tempfile.TemporaryDirectory() as tmp:
 for k,(st,s) in enumerate(phrases):
  p=Path(tmp)/f'{k}.wav'; subprocess.run(['espeak','-v','en-us','-s','170','-p','43','-w',str(p),s],check=True); sr,v=wavfile.read(p);g=gcd(sr,R);v=resample_poly(v.astype(float)/32768,R//g,sr//g);v=np.trim_zeros(v,'fb');v=sosfilt(butter(2,110,btype='highpass',fs=R,output='sos'),v);v=v/(np.max(np.abs(v))+1e-8);put(v,st,.49)
fade=np.minimum(t/.04,1)*np.minimum((12-t)/.22,1); mix=np.tanh(mix*1.15)*fade
out=Path(__file__).resolve().parent.parent/'public'/'soundtrack.wav'
out.parent.mkdir(exist_ok=True)
wavfile.write(out,R,np.int16(mix*32767))
