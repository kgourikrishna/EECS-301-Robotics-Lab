#!/usr/bin/env python
import roslib
import rospy
import threading
from fw_wrapper.srv import *
from map import *
import random
import math


# -----------SERVICE DEFINITION-----------
# allcmd REQUEST DATA
# ---------
# string command_type
# int8 device_id
# int16 target_val
# int8 n_dev
# int8[] dev_ids
# int16[] target_vals

# allcmd RESPONSE DATA
# ---------
# int16 val
# --------END SERVICE DEFINITION----------

# ----------COMMAND TYPE LIST-------------
# GetMotorTargetPosition
# GetMotorCurrentPosition
# GetIsMotorMoving
# GetSensorValue
# GetMotorWheelSpeed
# SetMotorTargetPosition
# SetMotorTargetSpeed
# SetMotorTargetPositionsSync
# SetMotorMode
# SetMotorWheelSpeed



# global array of directions
North = 1
East = 2
South = 3
West = 4
directions = (North, East, South, West)

dirMovedArray = []
cellsBeenIn = []
cellsToVisit = [[0,0]]


# make a cleared map to be explored
def newMap():
    newMap = EECSMap()
    newMap.clearObstacleMap()
    newMap.horizontalWalls[0][0] = 1
    newMap.verticalWalls[0][0] = 1
    return newMap

# map walls next to robot
def mapWalls(currentX, currentY, heading, myMap):
    print "Current X: " + str(currentX)
    print "Current Y: " + str(currentY)
    if getSensorValue(2) > 1600:
        print "Front wall seen"
        myMap.setObstacle(currentX,currentY,1,heading)
    if getSensorValue(5) > 50:
        print "Right Wall seen"
        if heading == West:
            d = 1
        else:
            d = heading + 1
        myMap.setObstacle(currentX, currentY, 1, d)
    if getSensorValue(1) > 50:
        print "Left Wall Seen"
        if heading == North:
            d = 4
        else:
            d = heading - 1
        myMap.setObstacle(currentX, currentY, 1, d)
        
# returns the opposite direction
def oppositeDirection(direction):
    if direction == North:
        return South
    if direction == South:
        return North
    if direction == West:
        return East
    if direction == East:
        return West
        

# wandering function for mapping
def wander(currentX, currentY, heading, myMap):
    mapWalls(currentX, currentY, heading, myMap)
    cellsToVisit.remove([currentX, currentY])
    if cellsBeenIn.count([currentX, currentY]) < 1:
        cellsBeenIn.append([currentX, currentY])
    wallArray = checkCellWalls(currentX, currentY, myMap)
    tag = 0
    for d in xrange(4):
        #print wallArray[d]
        if wallArray[d] == 0:
            if d == 0 and cellsBeenIn.count([currentX-1,currentY])<1:
                if cellsToVisit.count([currentX-1,currentY]) > 0:
                    cellsToVisit.remove([currentX-1,currentY])
                cellsToVisit.append([currentX-1,currentY])
                nextCell = [currentX-1,currentY]
                tag = 1
            if d == 1 and cellsBeenIn.count([currentX,currentY+1])<1:
                if cellsToVisit.count([currentX,currentY+1]) > 0:
                    cellsToVisit.remove([currentX,currentY+1])
                cellsToVisit.append([currentX,currentY+1])
                nextCell = [currentX,currentY+1]
                tag = 2
            if d == 2 and cellsBeenIn.count([currentX+1,currentY])<1:
                if cellsToVisit.count([currentX+1,currentY]) > 0:
                    cellsToVisit.remove([currentX+1,currentY])
                cellsToVisit.append([currentX+1,currentY])
                nextCell = [currentX+1,currentY]
                tag = 3
                print tag
            if d == 3 and cellsBeenIn.count([currentX,currentY-1])<1:
                if cellsToVisit.count([currentX,currentY-1]) > 0:
                    cellsToVisit.remove([currentX,currentY-1])
                cellsToVisit.append([currentX,currentY-1])
                nextCell = [currentX,currentY-1]
                tag = 4
    print cellsToVisit
    print cellsBeenIn
    if tag == 0:
        nextDirection = oppositeDirection(dirMovedArray.pop())
	if nextDirection == 1:
	    nextCell = [currentX-1,currentY]
	    cellsToVisit.append([currentX-1,currentY])
	elif nextDirection == 2:
	    nextCell = [currentX,currentY+1]
	    cellsToVisit.append([currentX,currentY+1])
	elif nextDirection == 3:
	    nextCell = [currentX+1,currentY]
	    cellsToVisit.append([currentX+1,currentY])
	else:
	    nextCell = [currentX,currentY-1]
	    cellsToVisit.append([currentX,currentY-1])
    else:
	#cellsToVisit.remove([currentX, currentY])
        nextDirection = tag
        dirMovedArray.append(tag)
    drive(nextDirection, heading)
    print "dir moved array: "
    print dirMovedArray
    stuff = [nextCell[0],nextCell[1],nextDirection]
    return stuff
            
# check walls
def checkCellWalls(cellx,celly, myMap):
    wallArray = [0,0,0,0]
    if myMap.horizontalWalls[cellx][celly] == 1:
	    wallArray[0] = 1
    if myMap.verticalWalls[cellx][celly+1] == 1:
	    wallArray[1] = 1
    if myMap.horizontalWalls[cellx+1][celly] == 1:
	    wallArray[2] = 1
    if myMap.verticalWalls[cellx][celly] == 1:
        wallArray[3] = 1
    return wallArray

#finding path function
def setMapCost(end,myMap):
    myMap.setCost(end[0],end[1], 1)
    #startx = start[0]
    #starty = start[1]
    #myMap.setCost(startx,starty,1)
    #startCell = [startx,starty]
    goalCell = (end[0],end[1])
    checkCells = [goalCell]
    for cell in checkCells:
	wallArray = checkCellWalls(cell[0],cell[1],myMap)
	print wallArray
	d = 1
	for wall in wallArray:
	    if wall == 0 and myMap.getNeighborCost(cell[0],cell[1],d) == 0:
	        myMap.setNeighborCost(cell[0],cell[1],d,myMap.getCost(cell[0],cell[1])+1)
	        if d == 1:
		    nextCell = [cell[0]-1,cell[1]]
		    checkCells.append(nextCell)
	        if d == 2:
		    nextCell = [cell[0],cell[1]+1]
		    checkCells.append(nextCell)
	        if d == 3:
		    nextCell = [cell[0]+1,cell[1]]
		    checkCells.append(nextCell)
	        if d == 4:
		    nextCell = [cell[0],cell[1]-1]
		    checkCells.append(nextCell)
	    d += 1

# find a path function
def findPath(cell,myMap, heading):
    newHeading = heading
    nextCell = cell
    wallArray = checkCellWalls(cell[0],cell[1],myMap)
    cellCost = myMap.getCost(cell[0],cell[1])
    if cellCost != 1:
         for d in directions:
            if myMap.getNeighborCost(cell[0],cell[1],d) == cellCost-1 and wallArray[d-1] == 0:
                print d
                print heading
                newHeading = drive(d, heading) 
                if d == 1:
                    nextCell = [cell[0]-1,cell[1]]
                    break
                elif d == 2:
                    nextCell = [cell[0],cell[1]+1]
                    break
                elif d == 3:
                    nextCell = [cell[0]+1,cell[1]]
                    break
                elif d == 4:
                    nextCell = [cell[0],cell[1]-1]
                    break
    print "Current Cell Position: " + str(nextCell)	
    return (nextCell, newHeading)

# drive function
def drive(direction, heading):
    heading = int(heading)
    if heading == 1:
        if direction == 2:
            turnRight90()
        elif direction == 3:
            turnRight90()
            turnRight90()
        elif direction == 4:
            turnLeft90()
    elif heading == 2:
	    if direction == 1:
	        turnLeft90()
	    elif direction == 3:
	        turnRight90()
	    elif direction == 4:
	        turnLeft90()
	        turnLeft90()
    elif heading == 3:
        if direction == 1:
            turnRight90()
            turnRight90()
        elif direction == 2:
            turnLeft90()
        elif direction == 4:
            turnRight90()
    elif heading == 4:
        if direction == 1:
            turnRight90()
        elif direction == 2:
            turnRight90()
            turnRight90()
        elif direction == 3:
            turnLeft90()
    forward(1)
    return direction

# set heading
def setHeading(heading):
    if heading == East:
	    turnLeft90()
	    turnLeft90()
	    turnLeft90()
    elif heading == North:
	    turnLeft90()
	    turnLeft90()
    elif heading == West:
	    turnLeft90()

# turn CCW 90 degrees
def turnLeft90():
    setMotorTargetPositionCommand(1, 362)
    setMotorTargetPositionCommand(3, 662)
    setMotorTargetPositionCommand(2, 662)
    setMotorTargetPositionCommand(4, 362)  
    pause() 

    setMotorWheelSpeed(10,1424)
    setMotorWheelSpeed(9,1424)
    setMotorWheelSpeed(7,1424)
    setMotorWheelSpeed(8,1424)
    pause(40)
          
    setMotorWheelSpeed(10,0)
    setMotorWheelSpeed(9,0)
    setMotorWheelSpeed(7,0)
    setMotorWheelSpeed(8,0)

# turn CW 90 degrees    
def turnRight90():
    setMotorTargetPositionCommand(1, 362)
    setMotorTargetPositionCommand(3, 662)
    setMotorTargetPositionCommand(2, 662)
    setMotorTargetPositionCommand(4, 362)  
    pause() 

    setMotorWheelSpeed(10,400)
    setMotorWheelSpeed(9,400)
    setMotorWheelSpeed(7,400)
    setMotorWheelSpeed(8,400)
    pause(40)
          
    setMotorWheelSpeed(10,0)
    setMotorWheelSpeed(9,0)
    setMotorWheelSpeed(7,0)
    setMotorWheelSpeed(8,0)

# pause function
def pause(x=1):
    a = 1000000
    i = 0
    while i < x*a:
        i += 1 

# wall follow left
def wallFollowLeft(squares=0, duration=16000000, sensorValue=60, j=0):
    target = 160
    setMotorTargetPositionCommand(3, 812)
    setMotorTargetPositionCommand(4, 212)
    pause()
    
    setMotorWheelSpeed(10,1424)
    setMotorWheelSpeed(9,400)
    setMotorWheelSpeed(7,1424)
    setMotorWheelSpeed(8,400)
    
    if squares != -1:
        i = 0
        while i < squares:
            while j < duration:
                j += 1000000
                if getSensorValue(1) < sensorValue:
                    j = wallFollowRight(squares-i,duration,10,j)
                else:
                    dist = target - getSensorValue(1)
                    if dist > 90:
                        dist = 90
                    elif dist < -90:
                        dist = -90
                    setMotorTargetPositionCommand(1, 212-dist)
                    setMotorTargetPositionCommand(2, 812-dist)
                pause()
            i+=1
        setMotorWheelSpeed(10,0)
        setMotorWheelSpeed(9,0)
        setMotorWheelSpeed(7,0)
        setMotorWheelSpeed(8,0)
        pause()
        return j
		
# wall follow that takes input gain
def gainWallFollow(gain):
    target = 160
    duration = 20
    k = 0
    total_error = 0
    
    setMotorTargetPositionCommand(3, 812)
    
    setMotorTargetPositionCommand(4, 212)
    pause(.5)
    
    setMotorWheelSpeed(10,1424)
    setMotorWheelSpeed(9,400)
    setMotorWheelSpeed(7,1424)
    setMotorWheelSpeed(8,400)
    
    while k < duration:
        k += 1
        rightSensor = getSensorValue(5)
        error = (target - rightSensor)
        dist = error*gain
        setMotorTargetPositionCommand(1, 212+dist)
        setMotorTargetPositionCommand(2, 812+dist)
        total_error += abs(error)
        pause(1)
    #setMotorWheelSpeed(10,0)
    #setMotorWheelSpeed(9,0)
    #setMotorWheelSpeed(7,0)
    #setMotorWheelSpeed(8,0)
    return total_error
	

#simulate annealing function
def anneal(gain):
    old_cost = gainWallFollow(gain)
    print old_cost
    setMotorWheelSpeed(10,0)
    setMotorWheelSpeed(9,0)
    setMotorWheelSpeed(7,0)
    setMotorWheelSpeed(8,0)
    raw_input("press 'Enter' to continue")
    T = 1.0
    T_min = .4
    alpha = .9
    with open("farFromWall.txt", "a") as f:
        f.write("Starting distance from wall: 15.5 cm \n")
        dataString = "T value: " + str(T)
        dataString = dataString + " T_min: " + str(T_min)
        dataString = dataString + " alpha: " + str(alpha)
        dataString = dataString + "\n\n"
        f.write(dataString)
    while T > T_min:
        i = 1
        while i<=10:
            new_sol = neighbor(gain, T)
            myString = "Gain: " + str(new_sol)
            new_cost = gainWallFollow(new_sol)
            myString = myString + " Cost: " + str(new_cost)
            ap = acceptance_probability(old_cost,new_cost,T)
            print "ap: " + str(ap)
            rand_int = random.random()
            print "old cost: " + str(old_cost) + " new_cost: " + str(new_cost)
            print "random number: " + str(rand_int)
            if ap > rand_int:
                gain = new_sol
                cost = new_cost
                old_cost = new_cost
                myString = myString + " PICKED"
            with open("trial4.txt", "a") as f:
                f.write(myString + "\n")
                print myString
            i+=1
            setMotorWheelSpeed(10,0)
            setMotorWheelSpeed(9,0)
            setMotorWheelSpeed(7,0)
            setMotorWheelSpeed(8,0)
            setMotorTargetPositionCommand(1, 212)
            setMotorTargetPositionCommand(3, 812)
            setMotorTargetPositionCommand(2, 812)
            setMotorTargetPositionCommand(4, 212)
            raw_input("press 'Enter' to continue")
        T = T*alpha
        #setMotorWheelSpeed(10,0)
        #setMotorWheelSpeed(9,0)
        #setMotorWheelSpeed(7,0)
        #setMotorWheelSpeed(8,0)
        #raw_input("press 'Enter' to continue")
        print "Temperature: " + str(T)
    setMotorWheelSpeed(10,0)
    setMotorWheelSpeed(9,0)
    setMotorWheelSpeed(7,0)
    setMotorWheelSpeed(8,0)
    return gain,cost
            
        
#neighboring function
def neighbor(gain, T):
    halfRange = .5*T
    print halfRange
    new_gain = random.uniform(gain-halfRange, gain + halfRange)
    while new_gain > 3.1:
        new_gain = random.uniform(gain-halfRange, gain + halfRange)
    
        #new_gain = random.uniform(.1,5)
        #if (abs(new_gain-gain) < .5):
        #    gain = new_gain
    return new_gain
    
    
#acceptance probability function
def acceptance_probability(old_cost,new_cost,T):
    #new_cost = round(new_cost, 20)
    #old_cost = round(old_cost, 20)
    exponent = round((old_cost-new_cost)/(40*T),50)
    if exponent > 50:
        exponent = 50
    if exponent < -1000:
        exponent = -1000
    ap = math.exp(exponent)
    return ap


# wall follow right
def wallFollowRight(squares=0, duration=16000000, sensorValue=60, k=0):
    target = 160
    
    setMotorTargetPositionCommand(3, 812)
    setMotorTargetPositionCommand(4, 212)
    pause()
    
    setMotorWheelSpeed(10,1424)
    setMotorWheelSpeed(9,400)
    setMotorWheelSpeed(7,1424)
    setMotorWheelSpeed(8,400)
    
    if squares != -1:
        i = 0
        while i < squares:
            while k < duration:
                #print (getSensorValue(5))
                #print "right j: " + str(k)
                k += 1000000
                rightSensor = getSensorValue(5)
                if rightSensor < sensorValue:
                    k = wallFollowLeft(squares-i,duration,10,k)
                else:
                    dist = target - rightSensor
                    if dist > 90:
                        dist = 90
                    elif dist < -90:
                        dist = -90
                    setMotorTargetPositionCommand(1, 212+dist)
                    setMotorTargetPositionCommand(2, 812+dist)
                pause()
            i+=1
        setMotorWheelSpeed(10,0)
        setMotorWheelSpeed(9,0)
        setMotorWheelSpeed(7,0)
        setMotorWheelSpeed(8,0)
        pause()
        return k 


# move forward
def forward(squares=0):
    setMotorTargetPositionCommand(1, 212)
    setMotorTargetPositionCommand(3, 812)
    setMotorTargetPositionCommand(2, 812)
    setMotorTargetPositionCommand(4, 212)
    pause(20)
    
    
    setMotorWheelSpeed(10,1424)
    setMotorWheelSpeed(9,400)
    setMotorWheelSpeed(7,1424)
    setMotorWheelSpeed(8,400)

    if getSensorValue(5) > getSensorValue(1):
        wallFollowRight(squares)
    elif getSensorValue(1) > getSensorValue(5):
        wallFollowLeft(squares)
    else:
        if squares != -1:
            i = 0
            while i < squares:
                pause(100)
                i+=1
            setMotorWheelSpeed(10,0)
            setMotorWheelSpeed(9,0)
            setMotorWheelSpeed(7,0)
            setMotorWheelSpeed(8,0)
            pause()

# drive backwards    
def backward(squares=0):
    setMotorTargetPositionCommand(1, 212)
    setMotorTargetPositionCommand(3, 812)
    setMotorTargetPositionCommand(2, 812)
    setMotorTargetPositionCommand(4, 212)
    pause(20)
    
    setMotorWheelSpeed(10,400)
    setMotorWheelSpeed(9,1424)
    setMotorWheelSpeed(7,400)
    setMotorWheelSpeed(8,1424)
    
    if squares != 0:
        i = 0
        while i < squares:
            pause(100)
            i+=1
        setMotorWheelSpeed(10,0)
        setMotorWheelSpeed(9,0)
        setMotorWheelSpeed(7,0)
        setMotorWheelSpeed(8,0)
        pause()
    
# move right
def right(squares=0):
    setMotorTargetPositionCommand(1, 512)
    setMotorTargetPositionCommand(3, 512)
    setMotorTargetPositionCommand(2, 512)
    setMotorTargetPositionCommand(4, 512)
    pause(20)
    
    setMotorWheelSpeed(7,400)
    setMotorWheelSpeed(8,400)
    pause(15)
    
    setMotorWheelSpeed(10,1424)
    setMotorWheelSpeed(9,1424)
    #setMotorWheelSpeed(7,400)
    #setMotorWheelSpeed(8,400)
    
    if squares != 0:
        i = 0
        while i < squares:
            pause(100)
            i+=1
        setMotorWheelSpeed(10,0)
        setMotorWheelSpeed(9,0)
        setMotorWheelSpeed(7,0)
        setMotorWheelSpeed(8,0)
        pause()

# move left        
def left(squares=0):
    setMotorTargetPositionCommand(1, 512)
    setMotorTargetPositionCommand(3, 512)
    setMotorTargetPositionCommand(2, 512)
    setMotorTargetPositionCommand(4, 512)
    pause(20)
    
    setMotorWheelSpeed(10,400)
    setMotorWheelSpeed(9,400)
    pause(15)
    
    setMotorWheelSpeed(7,1424)
    setMotorWheelSpeed(8,1424)
    
    if squares != 0:
        i = 0
        while i < squares:
            pause(100)
            i+=1
        setMotorWheelSpeed(10,0)
        setMotorWheelSpeed(9,0)
        setMotorWheelSpeed(7,0)
        setMotorWheelSpeed(8,0)
        pause()
    
# wrapper function to call service to get motor wheel speed
def getMotorWheelSpeed(motor_id):
    rospy.wait_for_service('allcmd')
    try:
        send_command = rospy.ServiceProxy('allcmd', allcmd)
        resp1 = send_command('GetMotorWheelSpeed', motor_id, 0, 0, [0], [0])
        return resp1.val
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e

# wrapper function to call service to set motor wheel speed
def setMotorWheelSpeed(motor_id, target_val):
    rospy.wait_for_service('allcmd')
    try:
        send_command = rospy.ServiceProxy('allcmd', allcmd)
        resp1 = send_command('SetMotorWheelSpeed', motor_id, target_val, 0, [0], [0])
        return resp1.val
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e

# wrapper function to call service to set motor target speed
def setMotorTargetSpeed(motor_id, target_val):
    rospy.wait_for_service('allcmd')
    try:
        send_command = rospy.ServiceProxy('allcmd', allcmd)
        resp1 = send_command('SetMotorTargetSpeed', motor_id, target_val, 0, [0], [0])
        return resp1.val
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e

# wrapper function to call service to set a motor target position
def setMotorMode(motor_id, target_val):
    rospy.wait_for_service('allcmd')
    try:
        send_command = rospy.ServiceProxy('allcmd', allcmd)
        resp1 = send_command('SetMotorMode', motor_id, target_val, 0, [0], [0])
        return resp1.val
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e

# wrapper function to call service to get sensor value
def getSensorValue(port):
    rospy.wait_for_service('allcmd')
    try:
        send_command = rospy.ServiceProxy('allcmd', allcmd)
        resp1 = send_command('GetSensorValue', port, 0, 0, [0], [0])
        return resp1.val
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e

# wrapper function to call service to set a motor target position
def setMotorTargetPositionCommand(motor_id, target_val):
    rospy.wait_for_service('allcmd')
    try:
        send_command = rospy.ServiceProxy('allcmd', allcmd)
	resp1 = send_command('SetMotorTargetPosition', motor_id, target_val, 0, [0], [0])
        return resp1.val
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e

# wrapper function to call service to get a motor's current position
def getMotorPositionCommand(motor_id):
    rospy.wait_for_service('allcmd')
    try:
        send_command = rospy.ServiceProxy('allcmd', allcmd)
	resp1 = send_command('GetMotorCurrentPosition', motor_id, 0, 0, [0], [0])
        return resp1.val
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e

# wrapper function to call service to check if a motor is currently moving
def getIsMotorMovingCommand(motor_id):
    rospy.wait_for_service('allcmd')
    try:
        send_command = rospy.ServiceProxy('allcmd', allcmd)
	resp1 = send_command('GetIsMotorMoving', motor_id, 0, 0, [0], [0])
        return resp1.val
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e
        
# define a thread which takes input
#class InputThread(threading.Thread):
#    def run(self):
#        self.daemon = True
#        while True:
#            self.last_user_input = input('input something: ')
            # do something based on the user input here
            # alternatively, let main do something with
            # self.last_user_input

# main
#it = InputThread()
#it.start()

# Main function
if __name__ == "__main__":
    rospy.init_node('example_node', anonymous=True)
    rospy.loginfo("Starting Group X Control Node...")
    
    setMotorTargetSpeed(1, 400)
    setMotorTargetSpeed(2, 400)
    setMotorTargetSpeed(3, 400)
    setMotorTargetSpeed(4, 400)
    
    setMotorMode(7,1)
    setMotorMode(8,1)
    setMotorMode(10,1)
    setMotorMode(9,1)
    
    setMotorWheelSpeed(10,0)
    setMotorWheelSpeed(9,0)
    setMotorWheelSpeed(7,0)
    setMotorWheelSpeed(8,0)
    
    #pause(20)
    
    myInput = raw_input("Enter command: ")
    if myInput == "path":
    # -----------------------------
    # ----code for path finding----
    
        startx = raw_input("Enter start x: ")
        starty = raw_input("Enter start y: ")
        heading = raw_input("Enter heading: ")
        endx = raw_input("Enter end x: ")
        endy = raw_input("Enter end y: ")
        startx = int(startx)
        starty = int(starty)
        heading = int(heading)
        endx = int(endx)
        endy = int(endy)

        startPosition = [startx,starty]
        endPosition = [endx,endy]

        myMap = EECSMap()
        setHeading(heading)
        setMapCost(endPosition,myMap)
        
        myMap.printCostMap()
        myMap.printObstacleMap()
        
        (currentCell,heading) = findPath(startPosition,myMap, heading)
        r = rospy.Rate(10)
        while not rospy.is_shutdown():
            (currentCell, heading) = findPath(currentCell, myMap, heading)
            r.sleep()
        
    # -----------------------------
    elif myInput == "map":
    
    #---- WALL MAPPING ----
        
        myMap = newMap()
        myMap.printObstacleMap()
        nextCell = wander(0,0,South,myMap)
       
        while cellsToVisit:
            nextCell = wander(nextCell[0], nextCell[1], nextCell[2], myMap)
            myMap.printObstacleMap()
        print cellsToVisit
    
    #----------------------
	
	#-----GAIN TUNING--------
    elif myInput == "gain":
    
        setMotorTargetPositionCommand(1, 212)
        setMotorTargetPositionCommand(3, 812)
        setMotorTargetPositionCommand(2, 812)
        setMotorTargetPositionCommand(4, 212)
        gain1 = raw_input("Enter first starting gain: ")
        [sol,cost] = anneal(float(gain1))
        print [sol,cost]
	    
	    #gain2 = raw_input("Enter second starting gain: ")
	    #gain3 = raw_input("Enter third starting gain: ")
	    
	    #tolerance = 10000
	    
	    #while tolerance > .01: #I have no idea what this value should be
		#	raw_input("Press enter to start test")
		#	error1 = gainWallFollow(int(gain1))
		#	raw_input("Press enter to start test")
		#	error2 = gainWallFollow(int(gain2))
		#	raw_input("Press enter to start test")
		#	error3 = gainWallFollow(int(gain3))
		#	max_error = max(error1, error2, error3)
		#	if error1 == max_error:
		#		gain1 = (gain2 + gain3)/2
		#		tolerance = abs(error2 - error3)
		#	elif error2 == max_error:
		#		gain2 = (gain1 + gain3)/2
		#		tolerance = abs(error1 - error3)
		#	elif error3 == max_error:
		#		gain3 = (gain1 + gain2)/2
		#		tolerance = abs(error1 - error2)
		#	print tolerance
		#	print "Gain 1: " + str(gain1) + " Gain 2: " + str(gain2) + " Gain 3: " + str(gain3)
		
    #------------------------
    
    #----------TEST STUFF------------
    elif myInput == "test":
        gainWallFollow(1)
	
	
    #forward(1)
    #forward(1)
    #turnLeft90()
    #forward(1)
    #forward(1)
    #print "done"
    
    #(currentCell,heading) = findPath(startPosition,myMap, heading)   

    # control loop running at 10hz
    r = rospy.Rate(10) # 10hz
    while not rospy.is_shutdown():
        # call function to get sensor value
        port = 2
        sensor_reading = getSensorValue(port)
        #rospy.loginfo("Sensor value at port %d: %f", 2, sensor_reading)
                
        #(currentCell, heading) = findPath(currentCell, myMap, heading)

    
        # sleep to enforce loop rate
        r.sleep()
        
        
