"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

export function DNAHelixCanvas({ className = "" }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let width = container.clientWidth || window.innerWidth;
    let height = container.clientHeight || window.innerHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(2, 0, 18);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    container.appendChild(renderer.domElement);

    // Lighting matching the Precision Genomics silver/lavender & monochromatic palette
    const ambientLight = new THREE.AmbientLight(0x22222a, 1.8);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xb9b6ca, 2.2);
    dirLight1.position.set(10, 15, 10);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x6d718a, 1.8);
    dirLight2.position.set(-10, -10, -5);
    scene.add(dirLight2);

    const pointLight = new THREE.PointLight(0xceccdc, 2.5, 40);
    pointLight.position.set(4, 2, 8);
    scene.add(pointLight);

    // Group to hold the entire DNA helix
    const dnaGroup = new THREE.Group();
    dnaGroup.position.set(3.2, 0, 0);
    dnaGroup.rotation.z = 0.25;
    dnaGroup.rotation.x = 0.1;
    scene.add(dnaGroup);

    // Materials for high-end organic aesthetic
    const sphereMat1 = new THREE.MeshPhongMaterial({
      color: 0xceccdc,
      emissive: 0x1f1f26,
      specular: 0xffffff,
      shininess: 90,
      transparent: true,
      opacity: 0.95,
    });

    const sphereMat2 = new THREE.MeshPhongMaterial({
      color: 0x8e8ca0,
      emissive: 0x14141a,
      specular: 0xceccdc,
      shininess: 70,
      transparent: true,
      opacity: 0.85,
    });

    const rungMat = new THREE.MeshPhongMaterial({
      color: 0x525260,
      emissive: 0x181820,
      specular: 0xb9b6ca,
      shininess: 40,
      transparent: true,
      opacity: 0.65,
    });

    // DNA Geometry Construction
    const numPairs = 75;
    const radius = 2.4;
    const twistFrequency = 0.18;
    const verticalSpacing = 0.38;

    const sphereGeoLarge = new THREE.SphereGeometry(0.18, 16, 16);
    const sphereGeoSmall = new THREE.SphereGeometry(0.12, 14, 14);

    for (let i = 0; i < numPairs; i++) {
      const y = (i - numPairs / 2) * verticalSpacing;
      const angle = i * twistFrequency;

      const x1 = Math.cos(angle) * radius;
      const z1 = Math.sin(angle) * radius;
      const x2 = Math.cos(angle + Math.PI) * radius;
      const z2 = Math.sin(angle + Math.PI) * radius;

      // Strand 1 Major Node
      const node1 = new THREE.Mesh(sphereGeoLarge, i % 2 === 0 ? sphereMat1 : sphereMat2);
      node1.position.set(x1, y, z1);
      dnaGroup.add(node1);

      // Strand 2 Major Node
      const node2 = new THREE.Mesh(sphereGeoLarge, i % 2 === 0 ? sphereMat2 : sphereMat1);
      node2.position.set(x2, y, z2);
      dnaGroup.add(node2);

      // Connecting Rung Cylinder
      const p1 = new THREE.Vector3(x1, y, z1);
      const p2 = new THREE.Vector3(x2, y, z2);
      const dist = p1.distanceTo(p2);
      const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);

      const rungGeo = new THREE.CylinderGeometry(0.045, 0.045, dist, 8);
      const rung = new THREE.Mesh(rungGeo, rungMat);
      rung.position.copy(mid);
      rung.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), p2.clone().sub(p1).normalize());
      dnaGroup.add(rung);

      // Intermediate Base Pair Beads on the rung
      const bead1 = new THREE.Mesh(sphereGeoSmall, sphereMat1);
      bead1.position.copy(p1).lerp(p2, 0.35);
      dnaGroup.add(bead1);

      const bead2 = new THREE.Mesh(sphereGeoSmall, sphereMat2);
      bead2.position.copy(p1).lerp(p2, 0.65);
      dnaGroup.add(bead2);
    }

    // Background Molecular Dust / Floating Fine Particles
    const particleCount = 280;
    const particleGeo = new THREE.BufferGeometry();
    const particlePos = new Float32Array(particleCount * 3);
    const particleVel: { x: number; y: number; z: number }[] = [];

    for (let i = 0; i < particleCount; i++) {
      particlePos[i * 3] = (Math.random() - 0.4) * 22;
      particlePos[i * 3 + 1] = (Math.random() - 0.5) * 28;
      particlePos[i * 3 + 2] = (Math.random() - 0.5) * 16;
      particleVel.push({
        x: (Math.random() - 0.5) * 0.005,
        y: (Math.random() - 0.5) * 0.006,
        z: (Math.random() - 0.5) * 0.005,
      });
    }
    particleGeo.setAttribute("position", new THREE.BufferAttribute(particlePos, 3));

    const particleMat = new THREE.PointsMaterial({
      color: 0xceccdc,
      size: 0.08,
      transparent: true,
      opacity: 0.55,
      blending: THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // Subtle interactive mouse tracking
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
      mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", handleMouseMove);

    // Render Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth rotation & organic floating movement
      dnaGroup.rotation.y = elapsedTime * 0.22;
      dnaGroup.position.y = Math.sin(elapsedTime * 0.6) * 0.35;

      // Gentle interactive parallax
      targetX = mouseX * 0.6;
      targetY = -mouseY * 0.4;
      camera.position.x += (2 + targetX - camera.position.x) * 0.04;
      camera.position.y += (targetY - camera.position.y) * 0.04;
      camera.lookAt(new THREE.Vector3(1.5, 0, 0));

      // Particles gentle drift
      const positions = particles.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        positions[i * 3 + 1] += Math.sin(elapsedTime + i) * 0.003;
        positions[i * 3] += Math.cos(elapsedTime * 0.8 + i) * 0.002;
      }
      particles.geometry.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth || window.innerWidth;
      const h = container.clientHeight || window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationFrameId);
      renderer.dispose();
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return <div ref={containerRef} className={`w-full h-full ${className}`} />;
}
