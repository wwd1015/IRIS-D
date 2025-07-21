# Deployment Guide - Portfolio Performance Dashboard

## Pre-Deployment Checklist

### 1. Code Cleanup ✅
- [x] Removed unused authentication module (`auth.py`)
- [x] Cleaned up `requirements.txt` to include only necessary dependencies
- [x] Updated test suite to match current functionality
- [x] Added proper documentation and docstrings
- [x] Removed unused files and scripts

### 2. File Structure Validation ✅
```
portfolio_performance_dashboard/
├── app.py                    # Main application ✅
├── requirements.txt          # Dependencies (cleaned) ✅
├── test_app.py              # Updated test suite ✅
├── README.md                # Comprehensive documentation ✅
├── DEPLOYMENT_GUIDE.md      # This guide ✅
├── data/                    # Data files ✅
│   ├── facilities.csv       # Core facility data
│   └── user_profiles.json   # User profiles (auto-created)
└── assets/                  # Static assets ✅
    └── style.css           # Custom styling
```

### 3. Dependencies ✅
Minimal required packages only:
- `dash>=2.14.0`
- `pandas>=2.0.0` 
- `numpy>=1.24.0`
- `plotly>=5.17.0`
- `gunicorn>=21.0.0`

### 4. Configuration Files ✅
- **`requirements.txt`**: Minimal dependencies for faster deployment
- **`README.md`**: Complete usage and deployment instructions

## Deployment Steps

### Option 1: VS Code Posit Connect Extension (Recommended)

1. **Install Extension**:
   - Install "Posit Connect" extension in VS Code
   - Configure server connection in settings

2. **Deploy**:
   - Open `app.py` in VS Code
   - Use Command Palette (`Cmd/Ctrl + Shift + P`)
   - Run: "Python: Publish to Posit Connect"
   - Select deployment target and configure settings

### Option 2: Command Line Deployment

1. **Install rsconnect-python**:
   ```bash
   pip install rsconnect-python
   ```

2. **Configure Server** (first time only):
   ```bash
   rsconnect add --server https://your-connect-server.com --name myserver --key your-api-key
   ```

3. **Deploy Application**:
   ```bash
   rsconnect deploy dash app.py --server myserver --title "Portfolio Performance Dashboard"
   ```

### Option 3: Git-backed Deployment

1. **Push to Git Repository**
2. **Configure Git-backed deployment in Posit Connect**
3. **Set build command**: `pip install -r requirements.txt`
4. **Set run command**: `python app.py`

## Testing Before Deployment

### Local Testing
```bash
# Run test suite
python test_app.py

# Start application locally
python app.py
# Visit: http://127.0.0.1:8050/
```

### Test Checklist
- [ ] All dependencies install correctly
- [ ] Data files load without errors
- [ ] Portfolio switching works
- [ ] Custom metrics can be created
- [ ] User profiles save/load correctly
- [ ] All visualizations render properly

## Post-Deployment Verification

### 1. Functional Tests
- [ ] Application loads successfully
- [ ] All tabs are accessible
- [ ] Portfolio dropdown populates
- [ ] Charts render correctly
- [ ] Custom metrics creation works
- [ ] Profile switching functions

### 2. Performance Tests
- [ ] Page load time < 5 seconds
- [ ] Chart interactions are responsive
- [ ] Auto-save notifications appear
- [ ] Large datasets load efficiently

### 3. User Access
- [ ] Application is accessible to intended users
- [ ] Authentication works (if enabled)
- [ ] Data security is maintained

## Troubleshooting

### Common Issues

**1. Import Errors**
```
Solution: Verify all dependencies in requirements.txt
Check: python test_app.py
```

**2. Data File Not Found**
```
Solution: Ensure data/ directory is included in deployment
Check: Files exist in correct relative path
```

**3. Port Conflicts**
```
Solution: Posit Connect handles port assignment automatically
Check: posit-connect.yml network configuration
```

**4. Memory Issues**
```
Solution: Increase memory allocation in posit-connect.yml
Current: 2Gi (should be sufficient for most use cases)
```

### Support Contacts

- **Technical Issues**: Contact Posit Connect Administrator
- **Application Issues**: Portfolio Management Team
- **Data Issues**: Data Engineering Team

## Maintenance

### Regular Tasks
- [ ] Monitor application performance
- [ ] Update data files as needed
- [ ] Review user feedback
- [ ] Apply security updates

### Backup Strategy
- User profiles are stored in `data/user_profiles.json`
- Consider regular backups of this file
- Data files should be updated via data pipeline

## Security Considerations

### Data Security
- No sensitive authentication data in codebase ✅
- User profiles contain only portfolio configurations ✅
- No hardcoded credentials or API keys ✅

### Access Control
- Relies on Posit Connect's authentication system
- No internal user management required
- Session management handled by framework

This deployment package is ready for production deployment to Posit Connect.