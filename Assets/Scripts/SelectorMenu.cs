using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using Microsoft.MixedReality.Toolkit;
using Microsoft.MixedReality.Toolkit.Input;

public class SelectorMenu : MonoBehaviour
{

    public GameObject selector;
    public GameObject cursor;
    public static SelectorMenu instance;


    //helper function
    private StateManager.SelectorType getInterface()
    {
        return StateManager.instance.selectorType;
    }


    // Start is called before the first frame update
    void Start()
    {
        this.Disappear();
        if (instance != null)
        {
            Debug.Log("Singleton error on selector menu");
        }
        instance = this;
    }

    // Update is called once per frame
    void Update()
    {
        
    }

    public void MoveAndDropForce()
    {
        if (!(this.getInterface() == StateManager.SelectorType.PointSelect || this.getInterface() == StateManager.SelectorType.Point || this.getInterface() == StateManager.SelectorType.GazeSelect || this.getInterface() == StateManager.SelectorType.Gaze))
        {
            if (selector != null)
            {
                TaskStateManager.instance.digitalTwinObject = selector;
                if (GameHandler.instance.contenderSelector == selector)
                {
                    GameHandler.instance.PlaceObject(selector.transform.position);
                }

            }
            this.Disappear();
            this.Cancel();
        }
        else
        {
            if (Selector.selectedObject != null)
            {
                if (GameHandler.instance.contenderSelector == Selector.selectedObject)
                {
                    GameHandler.instance.PlaceObject(selector.transform.position);
                }
            }
            this.Disappear();
            this.Cancel();
        }
    }

    public void MoveAndDrop()
    {
        if (!(this.getInterface() == StateManager.SelectorType.PointSelect || this.getInterface() == StateManager.SelectorType.GazeSelect))
        {
            if (selector != null)
            {
                TaskStateManager.instance.digitalTwinObject = selector;
                if (GameHandler.instance.contenderSelector == selector)
                {
                    GameHandler.instance.PlaceObject(selector.transform.position);
                }

            }
            this.Disappear();
            this.Cancel();
        } else
        {
            if (Selector.selectedObject != null)
            {
                if (GameHandler.instance.contenderSelector == Selector.selectedObject)
                {
                    GameHandler.instance.PlaceObject(selector.transform.position);
                }
            }
            this.Disappear();
            this.Cancel();
        }
    }

    public void MoveAndHold()
    {
        if (selector != null)
        {
            TaskStateManager.instance.digitalTwinObject = selector;
            //TaskStateManager.instance.SetTarget();
            //TaskStateManager.instance.SendTargetPosition();
            //TaskStateManager.instance.GetComponent<TaskStateManager>().GoTo();
        }
        this.Disappear();
    }

    public void Cancel()
    {
       if (selector != null && selector.GetComponent<Selector>() != null)
        {
            selector.GetComponent<Selector>().Cancel();

        } else
        {
            if (this.getInterface() == StateManager.SelectorType.PointSelect || this.getInterface() == StateManager.SelectorType.Gaze)
            {
                selector.GetComponent<Cursor>().Cancel();
            }
            
        }
    }

    public void Disappear()
    {
        gameObject.SetActive(false);
    }

    public void AppearOnFace()
    {
        gameObject.transform.position = Camera.main.transform.position + Camera.main.transform.forward * 0.5f;
        Vector3 cameraEulerAngles = Camera.main.transform.rotation.eulerAngles;
        Quaternion desiredRotation = Quaternion.Euler(0, cameraEulerAngles.y, 0);
        gameObject.transform.rotation = desiredRotation;
        gameObject.SetActive(true);
    }

    public void ApearAboveSelector()
    {
        
        gameObject.transform.position = new Vector3(selector.transform.position.x, selector.transform.position.y + 0.1f, +selector.transform.position.z);
        Vector3 cameraEulerAngles = Camera.main.transform.rotation.eulerAngles;
        Quaternion desiredRotation = Quaternion.Euler(cameraEulerAngles.x, cameraEulerAngles.y, cameraEulerAngles.z);
        gameObject.transform.rotation = desiredRotation;
        gameObject.SetActive(true);
    }
}
