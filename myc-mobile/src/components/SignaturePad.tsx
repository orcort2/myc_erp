import { StyleSheet, Text, View } from 'react-native';
import { WebView } from 'react-native-webview';

type Props = {
  label: string;
  onChange(value: string): void;
  value: string;
};

const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><style>body{margin:0;font-family:-apple-system;background:#fff}canvas{display:block;width:100%;height:180px;touch-action:none;background:#fff;border-bottom:1px solid #ccd6df}div{display:flex;gap:10px;padding:10px}button{flex:1;min-height:42px;border:0;border-radius:8px;font-size:15px;font-weight:700}#clear{background:#e8edf2;color:#263746}#save{background:#0067a8;color:#fff}</style></head><body><canvas id="pad"></canvas><div><button id="clear">Limpiar</button><button id="save">Usar firma</button></div><script>const c=document.getElementById('pad'),x=c.getContext('2d');function size(){const r=c.getBoundingClientRect(),d=devicePixelRatio||1;c.width=r.width*d;c.height=180*d;x.scale(d,d);x.lineWidth=2.4;x.lineCap='round';x.strokeStyle='#111'}size();let drawing=false;function p(e){const r=c.getBoundingClientRect(),t=e.touches?e.touches[0]:e;return[t.clientX-r.left,t.clientY-r.top]}c.addEventListener('touchstart',e=>{e.preventDefault();drawing=true;const q=p(e);x.beginPath();x.moveTo(q[0],q[1])},{passive:false});c.addEventListener('touchmove',e=>{e.preventDefault();if(!drawing)return;const q=p(e);x.lineTo(q[0],q[1]);x.stroke()},{passive:false});c.addEventListener('touchend',()=>drawing=false);document.getElementById('clear').onclick=()=>{x.clearRect(0,0,c.width,c.height);window.ReactNativeWebView.postMessage('')};document.getElementById('save').onclick=()=>window.ReactNativeWebView.postMessage(c.toDataURL('image/png'));</script></body></html>`;

export function SignaturePad({ label, onChange, value }: Props) {
  return (
    <View style={styles.wrapper}>
      <Text style={styles.label}>{label}</Text>
      <WebView
        originWhitelist={['*']}
        source={{ html }}
        onMessage={(event) => onChange(event.nativeEvent.data)}
        scrollEnabled={false}
        style={styles.webview}
      />
      <Text style={[styles.status, value ? styles.ready : undefined]}>
        {value ? 'Firma lista' : 'Firma y pulsa “Usar firma”'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { marginBottom: 18 },
  label: { fontSize: 17, fontWeight: '700', marginBottom: 8 },
  webview: { borderColor: '#b8c4cf', borderRadius: 10, borderWidth: 1, height: 245 },
  status: { color: '#7b4b00', fontSize: 13, marginTop: 6 },
  ready: { color: '#18723b', fontWeight: '700' },
});
