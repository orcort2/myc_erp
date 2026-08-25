import { useMemo, useRef } from 'react';
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';

import {
  emptySignatureCapture,
  SIGNATURE_MIN_STROKE_DISTANCE,
  type NormalizedPoint,
  type SignatureCapture,
} from './signature-flow-state';

type Props = {
  capture: SignatureCapture;
  disabled?: boolean;
  label: string;
  onChange(capture: SignatureCapture): void;
  onDrawingChange(active: boolean): void;
};

type PadMessage =
  | { type: 'capture'; capture: SignatureCapture }
  | { type: 'gesture'; active: boolean };

function safeInitialStrokes(strokes: NormalizedPoint[][]): string {
  return JSON.stringify(strokes).replace(/</g, '\\u003c');
}

function buildHtml(initialStrokes: NormalizedPoint[][]): string {
  return `<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<style>
html,body{width:100%;height:100%;margin:0;overflow:hidden;background:#fff;overscroll-behavior:none}
canvas{display:block;width:100%;height:100%;background:#fff;touch-action:none;-webkit-user-select:none;user-select:none}
</style></head><body><canvas id="pad" aria-label="Área de firma"></canvas><script>
const canvas=document.getElementById('pad');
const context=canvas.getContext('2d');
const MIN_STROKE_DISTANCE=${SIGNATURE_MIN_STROKE_DISTANCE};
function strokeDistance(stroke){
  let distance=0;
  for(let index=1;index<stroke.length;index+=1){
    distance+=Math.hypot(stroke[index].x-stroke[index-1].x,stroke[index].y-stroke[index-1].y);
  }
  return distance;
}
function isSignificantStroke(stroke){return stroke.length>=2&&strokeDistance(stroke)>=MIN_STROKE_DISTANCE}
let strokes=${safeInitialStrokes(initialStrokes)}.filter(isSignificantStroke);
let activePointer=null;
let activeStroke=null;
const send=(message)=>window.ReactNativeWebView.postMessage(JSON.stringify(message));
const point=(event)=>{const rect=canvas.getBoundingClientRect();return{x:Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width)),y:Math.max(0,Math.min(1,(event.clientY-rect.top)/rect.height))}};
function paintStroke(stroke){
  if(!stroke.length)return;
  const rect=canvas.getBoundingClientRect();
  context.beginPath();
  context.moveTo(stroke[0].x*rect.width,stroke[0].y*rect.height);
  if(stroke.length===1){context.lineTo(stroke[0].x*rect.width+.01,stroke[0].y*rect.height+.01)}
  for(let index=1;index<stroke.length;index+=1)context.lineTo(stroke[index].x*rect.width,stroke[index].y*rect.height);
  context.stroke();
}
function redraw(){
  const rect=canvas.getBoundingClientRect();
  const density=window.devicePixelRatio||1;
  canvas.width=Math.max(1,Math.round(rect.width*density));
  canvas.height=Math.max(1,Math.round(rect.height*density));
  context.setTransform(density,0,0,density,0,0);
  context.clearRect(0,0,rect.width,rect.height);
  context.strokeStyle='#0f2933';context.lineWidth=2.6;context.lineCap='round';context.lineJoin='round';
  strokes.forEach(paintStroke);
}
function emitCapture(){redraw();send({type:'capture',capture:{dataUrl:strokes.length?canvas.toDataURL('image/png'):'',hasDrawing:strokes.length>0,strokes}})}
function finish(event){
  if(activePointer===null||event.pointerId!==activePointer)return;
  event.preventDefault();
  try{canvas.releasePointerCapture(activePointer)}catch(error){}
  if(activeStroke&&!isSignificantStroke(activeStroke))strokes=strokes.filter((stroke)=>stroke!==activeStroke);
  activePointer=null;activeStroke=null;
  emitCapture();send({type:'gesture',active:false});
}
canvas.addEventListener('pointerdown',(event)=>{
  if(activePointer!==null||event.isPrimary===false)return;
  event.preventDefault();activePointer=event.pointerId;canvas.setPointerCapture(event.pointerId);
  activeStroke=[point(event)];strokes.push(activeStroke);redraw();send({type:'gesture',active:true});
});
canvas.addEventListener('pointermove',(event)=>{
  if(event.pointerId!==activePointer||!activeStroke)return;
  event.preventDefault();const next=point(event);const previous=activeStroke[activeStroke.length-1];
  if(Math.abs(next.x-previous.x)+Math.abs(next.y-previous.y)>.0008){activeStroke.push(next);redraw()}
});
canvas.addEventListener('pointerup',finish);
canvas.addEventListener('pointercancel',finish);
canvas.addEventListener('lostpointercapture',(event)=>{if(event.pointerId===activePointer)finish(event)});
window.clearSignature=()=>{activePointer=null;activeStroke=null;strokes=[];redraw();send({type:'capture',capture:{dataUrl:'',hasDrawing:false,strokes:[]}});send({type:'gesture',active:false})};
let resizeFrame=0;
const resize=()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{redraw();if(strokes.length)emitCapture()})};
new ResizeObserver(resize).observe(canvas);window.addEventListener('resize',resize);redraw();
</script></body></html>`;
}

export function MobileSignaturePad({ capture, disabled = false, label, onChange, onDrawingChange }: Props) {
  const webViewRef = useRef<WebView>(null);
  const initialStrokesRef = useRef(capture.strokes);
  const { height, width } = useWindowDimensions();
  const isLandscape = width > height;
  const canvasHeight = isLandscape
    ? Math.max(150, Math.min(205, height * 0.38))
    : Math.max(190, Math.min(250, height * 0.29));
  const html = useMemo(() => buildHtml(initialStrokesRef.current), []);
  const source = useMemo(() => ({ html }), [html]);

  function handleMessage(event: WebViewMessageEvent) {
    try {
      const message = JSON.parse(event.nativeEvent.data) as PadMessage;
      if (message.type === 'gesture') onDrawingChange(message.active);
      if (message.type === 'capture') onChange(message.capture);
    } catch {
      onDrawingChange(false);
    }
  }

  function clear() {
    if (disabled) return;
    onDrawingChange(false);
    onChange(emptySignatureCapture());
    webViewRef.current?.injectJavaScript('window.clearSignature(); true;');
  }

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View>
          <Text style={styles.label}>{label}</Text>
          <Text style={[styles.status, capture.hasDrawing && styles.ready]}>
            {capture.hasDrawing ? 'Lista para continuar' : 'Pendiente'}
          </Text>
        </View>
        <Pressable disabled={disabled} onPress={clear} style={styles.clearButton}>
          <Text style={styles.clearText}>Limpiar</Text>
        </Pressable>
      </View>
      <View style={[styles.canvasFrame, { height: canvasHeight }]}>
        <WebView
          bounces={false}
          javaScriptEnabled
          nestedScrollEnabled={false}
          onMessage={handleMessage}
          onTouchCancel={() => onDrawingChange(false)}
          onTouchEnd={() => onDrawingChange(false)}
          onTouchStart={() => onDrawingChange(true)}
          originWhitelist={['*']}
          overScrollMode="never"
          ref={webViewRef}
          scrollEnabled={false}
          showsHorizontalScrollIndicator={false}
          showsVerticalScrollIndicator={false}
          source={source}
          style={styles.webview}
          textInteractionEnabled={false}
        />
        {disabled && <View pointerEvents="auto" style={styles.disabledOverlay} />}
      </View>
      <Text style={styles.hint}>Firma dentro del recuadro con el dedo.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#fff', borderColor: '#d6e1e6', borderRadius: 18, borderWidth: 1, padding: 14 },
  canvasFrame: { backgroundColor: '#fff', borderColor: '#9fb2bc', borderRadius: 14, borderWidth: 1.5, overflow: 'hidden' },
  clearButton: { alignItems: 'center', justifyContent: 'center', minHeight: 44, minWidth: 78, paddingHorizontal: 12 },
  clearText: { color: '#08756f', fontSize: 15, fontWeight: '800' },
  disabledOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(255,255,255,.38)' },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  hint: { color: '#6a7881', fontSize: 12, marginTop: 9 },
  label: { color: '#173746', fontSize: 16, fontWeight: '800' },
  ready: { color: '#08756f' },
  status: { color: '#9a5b00', fontSize: 12, fontWeight: '700', marginTop: 3 },
  webview: { backgroundColor: '#fff', flex: 1 },
});
