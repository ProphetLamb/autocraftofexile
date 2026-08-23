// place files you want to import through the `$lib` alias in this folder.

export function deepEqual(obj1: unknown, obj2: unknown) {

    if(obj1 === obj2) // it's just the same object. No need to compare.
        return true;

    if(isPrimitive(obj1) && isPrimitive(obj2)) // compare primitives
        return obj1 === obj2;

    // @ts-expect-error isPromitive type check
    if(Object.keys(obj1).length !== Object.keys(obj2).length)
        return false;

    // compare objects with same number of keys
    // @ts-expect-error isPromitive type check
    for(const key in obj1)
    {
    // @ts-expect-error isPromitive type check
        if(!(key in obj2)) return false; //other object doesn't have this prop
    // @ts-expect-error isPromitive type check
        if(!deepEqual(obj1[key], obj2[key])) return false;
    }

    return true;
}

//check if value is primitive
function isPrimitive(obj: unknown)
{
    return (obj !== Object(obj));
}