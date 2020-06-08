from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
import cv2
import numpy as np
import time
import math
import pynput.keyboard as pk
from pynput.keyboard import Key
import pynput.mouse as pm
from pynput.mouse import Button as button
import wx
import threading

pwsd = 12345
# region of interest (ROI) coordinates
top, right, bottom, left = 10, 300, 300, 600
l = 0
cap = None
sdThresh = 10
swipeTresh = 10


def distMap(frame1, frame2):
    """outputs pythagorean distance between two frames"""
    frame1_32 = np.float32(frame1)
    frame2_32 = np.float32(frame2)
    diff32 = frame1_32 - frame2_32
    norm32 = np.sqrt(diff32[:,:,0]**2 + diff32[:,:,1]**2 + diff32[:,:,2]**2)/np.sqrt(255**2 + 255**2 + 255**2)
    dist = np.uint8(norm32*255)
    return dist


def segmentation(flag, ms, ppt):
    pptvar = 5
    mouse = pm.Controller()
    app = wx.App(False)
    prev = []
    (srx, sry) = wx.GetDisplaySize()
    (camx,camy) = (320,240)
    (prevx, prevy) = (0,0)
    global l
    global cap
    cap = cv2.VideoCapture(0)
    _, frame1 = cap.read()
    _, frame2 = cap.read()

    while(1):
        
        try:  #an error comes if it does not find anything in window as it cannot find contour of max area
          #therefore this try error statement
          
            ret, frame = cap.read()
            rows, cols, _ = np.shape(frame)
            frame=cv2.flip(frame,1)
            kernel = np.ones((3,3),np.uint8)
             #define region of interest
            roi = frame[top:bottom, right:left]
            cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)    
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
     
            # define range of skin color in HSV
            lower_skin = np.array([0, 20, 80], dtype=np.uint8)
            upper_skin = np.array([35,255,255], dtype=np.uint8)

        
            #extract skin colur imagw  
            mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
            #blur the image
            mask = cv2.GaussianBlur(mask,(5,5),100)
        
            #find contours
            contours,hierarchy= cv2.findContours(mask,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        
            #find contour of max area(hand)
            cnt = max(contours, key = lambda x: cv2.contourArea(x))
            print("----------------------------------")
        
            #approx the contour a little
            epsilon = 0.0005*cv2.arcLength(cnt,True)
            approx= cv2.approxPolyDP(cnt,epsilon,True)
       
            #make convex hull around hand
            hull = cv2.convexHull(cnt)
        
             #define area of hull and area of hand
            areahull = cv2.contourArea(hull)
            areacnt = cv2.contourArea(cnt)
            #find the percentage of area not covered by hand in convex hull
            arearatio=((areahull-areacnt)/areacnt)*100
    
            #find the defects in convex hull with respect to hand
            hull = cv2.convexHull(approx, returnPoints=False)
            defects = cv2.convexityDefects(approx, hull)
        
            # l = no. of defects
            l = 0
            far = 0
        
            #code for finding no. of defects due to fingers
            for i in range(defects.shape[0]):
                s,e,f,d = defects[i,0]
                start = tuple(approx[s][0])
                end = tuple(approx[e][0])
                far = tuple(approx[f][0])
                pt= (100,180)
            
                # find length of all sides of triangle
                a = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
                b = math.sqrt((far[0] - start[0])**2 + (far[1] - start[1])**2)
                c = math.sqrt((end[0] - far[0])**2 + (end[1] - far[1])**2)
                s = (a+b+c)/2
                ar = math.sqrt(s*(s-a)*(s-b)*(s-c))
            
                #distance between point and convex hull
                d=(2*ar)/a
            
                # apply cosine rule here
                angle = math.acos((b**2 + c**2 - a**2)/(2*b*c)) * 57
            
                # ignore angles > 90 and ignore points very close to convex hull(they generally come due to noise)
                if angle <= 90 and d>30:
                    l += 1
                    cv2.circle(roi, far, 3, [255,0,0], -1)
            
                #draw lines around hand
                cv2.line(roi,start, end, [0,255,0], 2)
            l+=1
            #print corresponding gestures which are in their ranges
            font = cv2.FONT_HERSHEY_SIMPLEX
            dist = distMap(frame1, frame)
            frame1 = frame2
            frame2 = frame
            mod = cv2.GaussianBlur(dist, (9,9), 0)
            _, thresh = cv2.threshold(mod, 100, 255, 0)
            _, stDev = cv2.meanStdDev(mod)
            M = cv2.moments(cnt)
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

            if (ppt and stDev > 10) :
                keyboard = pk.Controller()
                if( len(prev) > 5 and center[0] - prev[0][0] < 10):
                    print("left", center[0] - prev[0][0])
                    keyboard.press(Key.up)
                    keyboard.release(Key.up)
                    prev = [ ]
                elif(len(prev)> 5 and center[0] - prev[0][0] > 10) :
                    print('right', center[0] - prev[0][0] )
                    keyboard.press(Key.down)
                    keyboard.release(Key.down)
                    prev = [ ]
                else :
                    prev.append(center)
            elif (ppt) :
                pptvar = pptvar - 1
                if(pptvar == 0):
                    prev = []
                    pptvar = 5
               
            elif (ms) :
                if l==1:
                    if areacnt<2000:
                        cv2.putText(frame,'Put hand in the box',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
                    else:
                        if arearatio<12:
                            l = 0
                            cv2.putText(frame,'0',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)                 
                        else:
                            cv2.putText(frame,'Mouse Left Click',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
                            if(0) :
                                mouse.press(button.left)
                       
                elif l==2:
                
                    cv2.putText(frame,'Cursor Movement',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
                    if(flag) :
                        print(far)
                        if (stDev > sdThresh) :
                            #print(prevx - far[0], '----', prevy - far[1])
                            if(prevx - far[0] > 40):
                                print("left" , prevx - far[0])
                                mouse.position = (mouse.position[0] - (prevx - far[0] + 40) , mouse.position[1])
                                prevx = far[0]
                            if(prevx - far[0] < -40):
                                print("right", prevx - far[0])
                                mouse.position = (mouse.position[0] - (prevx - far[0]) +  40 , mouse.position[1])
                                prevx = far[0]
                            if(prevy - far[1] > 20):
                                print("up", prevy - far[1])
                                mouse.position = (mouse.position[0], mouse.position[1] - (prevy - far[1]  + 40))
                                prevy = far[1]
                            if(prevy - far[1] < -20):
                                print("down", prevy - far[1])
                                mouse.position = (mouse.position[0], mouse.position[1] - (prevy - far[1]) + 40)
                                prevy = far[1]
                            
                        
                elif l==3:    
                    cv2.putText(frame,'Mouse Right Click',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
                    if (0) :
                        mouse.press(button.right)

                elif l == 4:
                    cv2.putText(frame,'4',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)

                elif l == 5:
                    cv2.putText(frame,'5',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
                    
                
            
        except Exception as e:
            print(e)
        cv2.imshow('mask', mask)
        cv2.imshow('frame',frame)
    
        k = cv2.waitKey(5) & 0xFF
        if k == 27:
            break
    
    cv2.destroyAllWindows()
    cap.release()

def mouseThread():
    t3 = threading.Thread(target = segmentation, args = (1,1 ,0,))
    t3.start()

def pptThread():
    t4 = threading.Thread(target = segmentation, args = (1,0,1,))
    t4.start()
    
    
def submit(pwd):
    print(cap)
    pd = pwd.get("1.0", "end")
    pd = int(pd)
    if(pd == pwsd):
        startwin = Toplevel()
        startwin.title("MOUSE CONTROL")
        ent=Button(startwin,text="START MOUSE CTRL",command=lambda:mouseThread())
        ent.grid(row=1,column=1)
        ent=Button(startwin,text="START PPT CTRL",command=lambda:pptThread())
        ent.grid(row=1,column=5)
    else :
        mess=messagebox.showinfo("ERROR","WRONG PASSWORD")



def bckspace(pwd):
    pd = pwd.get("1.0", "end")
    #pwd.configure(state='normal')
    pwd.set( pd[:-1])
    #pwd.configure(state='disabled')


def enter(pwd):
    pwd.configure(state='normal')
    pwd.insert('end', l)
    pwd.configure(state='disabled')
    

def segThread(ent):
    ent.grid_remove()
    t2 = threading.Thread(target = segmentation, args = (0,1,0,))
    t2.start()
    

    
def gui():
    entrpwdwin = Toplevel()
    entrpwdwin.title("Enter Passowrd")
    pwd = Text(entrpwdwin, state='disabled', width=10, height=1)
    pwd.grid(row = 0, column = 0)
    ent=Button(entrpwdwin,text="START",command=lambda:segThread(ent))
    ent.grid(row=1,column=1)
    st=Button(entrpwdwin,text="ENTER",command=lambda:enter(pwd))
    st.grid(row=1, column=5)
    bks=Button(entrpwdwin,text="BACKSPC",command=lambda:bckspace(pwd))
    bks.grid(row=1,column=7)
    sub=Button(entrpwdwin,text="SUBMIT",command=lambda:submit(pwd))
    sub.grid(row=1, column=9)
    
def guiThread():
   t1 = threading.Thread(target = gui)
   t1.start()
    
    
t=Tk()

fb=Button(t,text="ENTER PASSWORD", command=lambda:guiThread())
fb.grid(row=0,column=1)
t.title("PROJECT")
t.mainloop()


