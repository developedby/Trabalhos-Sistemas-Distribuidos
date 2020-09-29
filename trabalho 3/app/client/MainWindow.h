#ifndef MY_MAIN_WINDOW_H 
#define MY_MAIN_WINDOW_H

#include "gui.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT
    Ui::MainWindow _ui;

private slots:
    void _onAddQuoteBtn();
    void _onRemoveQuoteBtn();
    void _onAddAlertBtn();
    void _onCreateOrderBtn();
    void _onUpdateBtn();
    
public:
    MainWindow();

};

#endif