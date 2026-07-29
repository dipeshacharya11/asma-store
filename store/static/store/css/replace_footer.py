import sys

def main():
    filename = 'base.css'
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find start and end of footer section
    start_marker = '/* ---------- Footer ---------- */'
    end_marker = '/* =========================================================================='
    
    start_idx = -1
    end_idx = -1
    for i, line in enumerate(lines):
        if start_marker in line:
            start_idx = i
        if end_marker in line and start_idx != -1:
            end_idx = i
            break
    
    if start_idx == -1 or end_idx == -1:
        print("Could not find footer markers")
        sys.exit(1)
    
    # New footer content
    new_footer = '''/* ==========================================================================
   FOOTER
   ========================================================================== */

/* ---------- Footer ---------- */
/*==========================================
FOOTER
==========================================*/

.site-footer{
    background:linear-gradient(
        180deg,
        #184E7A,
        #235C93,
        #173F67
    );
    color:#fff;
    margin-top:clamp(40px, 6vw, 80px);
    overflow:hidden;
}

.site-footer .container{
    max-width:1360px;
    margin:auto;
    padding:clamp(50px, 8vw, 70px) clamp(20px, 4vw, 30px) clamp(20px, 4vw, 30px);
}

/* Footer grid */
.footer-grid{
    display:grid;
    gap:clamp(20px, 4vw, 55px);
    /* For desktop: 5 columns */
    grid-template-columns: 2fr 1fr 1fr 1fr 1.5fr;
}

@media (max-width: 768px) {
    .footer-grid{
        grid-template-columns: repeat(2, 1fr);
    }
    .footer-brand{
        grid-column: 1 / -1;
        grid-row: 1;
    }
    .footer-column.shop{
        grid-column: 1;
        grid-row: 2;
    }
    .footer-column.support{
        grid-column: 2;
        grid-row: 2;
    }
    .footer-column.company{
        grid-column: 1;
        grid-row: 3;
    }
    .footer-column.footer-newsletter{
        grid-column: 2;
        grid-row: 3;
    }
}

/* Footer brand */
.footer-brand{
    display:flex;
    flex-direction:column;
    align-items:center;
    text-align:center;
}

.footer-logo img{
    width:clamp(120px, 20vw, 180px);
    height:auto;
    filter:brightness(0) invert(1);
    margin-bottom:clamp(10px, 2vw, 20px);
}

.footer-description{
    font-size:clamp(14px, 1.8vw, 16px);
    line-height:1.8;
    color:rgba(255,255,255,.72);
    max-width:90%;
    margin-bottom:clamp(20px, 2.5vw, 28px);
    margin-left:auto;
    margin-right:auto;
}

.social-row{
    display:flex;
    gap:clamp(10px, 2vw, 14px);
    margin-top:clamp(10px, 2vw, 25px);
    justify-content:center;
}

.social-row a{
    width:clamp(30px, 5vw, 44px);
    height:clamp(30px, 5vw, 44px);
    border-radius:50%;
    background:rgba(255,255,255,.08);
    display:flex;
    justify-content:center;
    align-items:center;
    transition:.3s;
}

.social-row a:hover{
    background:#4A88D4;
    transform:translateY(-4px);
}

.social-row svg{
    width:clamp(12px, 2vw, 18px);
    height:clamp(12px, 2vw, 18px);
    stroke:#fff;
    fill:none;
    stroke-width:1.8;
}

/* Footer columns */
.footer-column h5{
    font-size:clamp(16px, 2.5vw, 20px);
    margin-bottom:clamp(12px, 2vw, 20px);
    font-weight:600;
    position:relative;
}

.footer-column h5::after{
    content:"";
    display:block;
    width:clamp(20px, 4vw, 38px);
    height:clamp(1px, 0.5vw, 2px);
    background:#6FA6C5;
    margin-top:10px;
}

.footer-column ul{
    list-style:none;
    padding:0;
    margin:0;
}

.footer-column li{
    margin-bottom:clamp(8px, 1.5vw, 12px);
}

.footer-column a{
    text-decoration:none;
    color:rgba(255,255,255,.72);
    transition:.25s;
}

.footer-column a:hover{
    color:#fff;
    padding-left:clamp(4px, 1vw, 6px);
}

/* Newsletter form */
.newsletter-form{
    display:flex;
    height:clamp(40px, 6vw, 52px);
    border-radius:999px;
    overflow:hidden;
    background:#fff;
}

.newsletter-form input{
    flex:1;
    padding:0 clamp(12px, 2vw, 18px);
    border:none;
    outline:none;
    font-size:clamp(14px, 1.6vw, 16px);
}

.newsletter-form button{
    width:clamp(48px, 8vw, 58px);
    background:#235C93;
    border:none;
    display:flex;
    justify-content:center;
    align-items:center;
    cursor:pointer;
    transition:.3s;
}

.newsletter-form button:hover{
    background:#4A88D4;
}

/* Footer bottom */
.footer-bottom{
    margin-top:clamp(30px, 4vw, 60px);
    padding-top:clamp(15px, 2vw, 25px);
    border-top:1px solid rgba(255,255,255,.12);
    text-align:center;
    color:rgba(255,255,255,.65);
    font-size:clamp(12px, 1.5vw, 14px);
}
'''
    # Convert to list of lines, ensuring each line ends with newline
    new_footer_lines = [line + '\n' for line in new_footer.split('\n') if line != '' or True]
    # Ensure the last line has newline if not already
    if new_footer_lines and not new_footer_lines[-1].endswith('\n'):
        new_footer_lines[-1] += '\n'
    
    # Replace the footer section
    # We want to replace from start_idx to end_idx-1 (since end_idx is the line with the next marker)
    new_lines = lines[:start_idx] + new_footer_lines + lines[end_idx:]
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("Footer replaced successfully.")

if __name__ == '__main__':
    main()
