import React from 'react';
import mycLogo from '../assets/myc-logo.png';

function BrandLockup({ compact = false, subtitle = null }) {
  return (
    <div className={compact ? 'brand-lockup brand-lockup--compact' : 'brand-lockup'}>
      <img alt="MYC" src={mycLogo} />
      <div>
        <strong>MYC SYSTEM</strong>
        {subtitle ? <span>{subtitle}</span> : null}
      </div>
    </div>
  );
}



export default BrandLockup;
