import React, { useRef, useEffect, memo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Environment } from '@react-three/drei';
import * as THREE from 'three';
import { createNoise4D } from 'simplex-noise';

const noise4D = createNoise4D();

const GlacisphereMesh = memo(({ intensity = 0.5, speed = 0.012, ampBase = 0.12, ampVar = 0.18 }) => {
  const mesh = useRef();
  const origPositions = useRef();
  const tRef = useRef(0);

  useEffect(() => {
    if (mesh.current) {
      const pos = mesh.current.geometry.attributes.position.array;
      origPositions.current = new Float32Array(pos);
    }
  }, []);

  useFrame(() => {
    tRef.current += speed;
    const t = tRef.current;
    const geometry = mesh.current.geometry;
    const pos = geometry.attributes.position;
    if (!origPositions.current) return;
    
    for (let i = 0; i < pos.count; i++) {
      const ox = origPositions.current[i * 3];
      const oy = origPositions.current[i * 3 + 1];
      const oz = origPositions.current[i * 3 + 2];
      const len = Math.sqrt(ox * ox + oy * oy + oz * oz);
      const nx = ox / len;
      const ny = oy / len;
      const nz = oz / len;
      
      const noise = noise4D(nx * 1.5, ny * 1.5, nz * 1.5, t * 0.7);
      const amp = ampBase + ampVar * noise;
      const r = 1.2 * (1 + amp * intensity);
      pos.setXYZ(i, nx * r, ny * r, nz * r);
    }
    pos.needsUpdate = true;
    geometry.computeVertexNormals();
  });

  return (
    <mesh ref={mesh} position={[0, 0, 0]}>
      <icosahedronGeometry args={[1.2, 64]} />
      <meshPhysicalMaterial
        color={new THREE.Color('#FFD700')}
        roughness={0.08}
        metalness={0.6}
        transmission={0.7}
        thickness={1.1}
        ior={1.45}
        reflectivity={0.7}
        clearcoat={0.7}
        clearcoatRoughness={0.15}
        attenuationColor={new THREE.Color('#FFC300')}
        attenuationDistance={0.7}
        transparent
        opacity={0.98}
      />
    </mesh>
  );
});

export default function GlassyBlob({ 
  intensity = 0.5, 
  mode = 'idle', 
  speed, 
  ampBase, 
  ampVar,
  size = 420 
}) {
  const dynamicSpeed = speed !== undefined ? speed : 
    mode === 'speaking' ? 0.055 : 
    mode === 'listening' ? 0.008 : 0.012;

  const dynamicAmpBase = ampBase !== undefined ? ampBase :
    mode === 'listening' ? 0.22 : 
    mode === 'speaking' ? 0.18 : 0.12;

  const dynamicAmpVar = ampVar !== undefined ? ampVar :
    mode === 'listening' ? 0.32 : 
    mode === 'speaking' ? 0.28 : 0.18;

  return (
    <div 
      style={{ 
        width: size, 
        height: size, 
        margin: 'auto', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        transition: 'all 0.3s ease'
      }}
    >
      <Canvas camera={{ position: [0, 0, 3.5], fov: 50 }} style={{ 
        background: 'transparent',
        width: '100%',
        height: '100%'
      }}>
        <ambientLight intensity={0.8} />
        <pointLight position={[10, 10, 10]} intensity={1.5} color={'#fff8e1'} />
        <GlacisphereMesh 
          intensity={intensity} 
          speed={dynamicSpeed} 
          ampBase={dynamicAmpBase} 
          ampVar={dynamicAmpVar} 
        />
        <Environment files="/env/city.hdr" />
      </Canvas>
    </div>
  );
}
